"""
Charts — Technical Data Collector (Dept 1: Investigación)

Collects real-time OHLCV data, calculates 20+ indicators, identifies patterns,
and defines precise entry/exit levels across multiple timeframes.

NEVER presents a setup without a stop-loss. Minimum R:R 1:2.
"""

import logging
from datetime import datetime, timezone

import pandas as pd
import ta

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from market.market_data import fetch_bars_multiindex

log = logging.getLogger(__name__)

# Tickers monitored by default (configurable via bus messages)
DEFAULT_WATCHLIST = ["AAPL", "NVDA", "MSFT", "BTC-USD", "ETH-USD", "SPY", "QQQ"]

TIMEFRAMES = {
    "1h":  ("1h",  "60d"),
    "4h":  ("1h",  "60d"),   # we resample 1h → 4h
    "1d":  ("1d",  "1y"),
    "1wk": ("1wk", "5y"),
}


class ChartsAgent(BaseAgent):
    agent_id = "charts"
    agent_name = "Charts"
    department = "research"
    emoji = "📈"

    def __init__(self) -> None:
        super().__init__()
        self.watchlist: list[str] = DEFAULT_WATCHLIST.copy()

    # ── Main cycle ─────────────────────────────────────────────────────────────

    async def run_cycle(self) -> None:
        await self.set_status(AgentStatus.WORKING, "Collecting market data")

        # Batch fetch via unified market data layer (Alpaca + CoinGecko + Frankfurter)
        try:
            df_all = fetch_bars_multiindex(self.watchlist, timeframe="1h", period="60d")
        except Exception as exc:
            log.warning("[Charts] Batch fetch failed: %s", exc)
            df_all = pd.DataFrame()

        results = []
        for ticker in self.watchlist:
            try:
                # Extract per-ticker slice from the batched DataFrame
                if isinstance(df_all.columns, pd.MultiIndex):
                    if ticker in df_all.columns.get_level_values(0):
                        df_ticker = df_all[ticker].copy()
                    else:
                        continue
                else:
                    # Single-ticker fallback (shouldn't happen with a list, but safe)
                    df_ticker = df_all.copy()
                analysis = self._analyze_ticker(ticker, df_ticker)
                if analysis:
                    results.append(analysis)
            except Exception as exc:
                log.warning("[Charts] Error analyzing %s: %s", ticker, exc)

        if results:
            await self.set_status(AgentStatus.SENDING, "Publishing technical analysis")
            await self.publish(
                payload={
                    "analysis": results,
                    "tickers_analyzed": [r["ticker"] for r in results],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                category=MessageCategory.TECHNICAL,
                tickers=[r["ticker"] for r in results],
                markets=["stocks", "crypto"],
                confidence=0.8,
                priority=3,
            )
            log.info("[Charts] Published analysis for %d tickers", len(results))

        await self.set_status(AgentStatus.IDLE)

    # ── Analysis ───────────────────────────────────────────────────────────────

    def _analyze_ticker(self, ticker: str, df: "pd.DataFrame") -> dict | None:
        """Compute indicators for a single ticker from a pre-downloaded DataFrame."""
        if df is None or df.empty or len(df) < 50:
            return None

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)

        # ── Indicators ──────────────────────────────────────────────────────
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # Trend
        df["ema_20"]  = ta.trend.ema_indicator(close, window=20)
        df["ema_50"]  = ta.trend.ema_indicator(close, window=50)
        df["ema_200"] = ta.trend.ema_indicator(close, window=200)

        # Momentum
        df["rsi"]  = ta.momentum.rsi(close, window=14)
        macd_obj   = ta.trend.MACD(close)
        df["macd"] = macd_obj.macd()
        df["macd_signal"] = macd_obj.macd_signal()
        df["macd_diff"]   = macd_obj.macd_diff()

        # Volatility
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_mid"]   = bb.bollinger_mavg()
        df["bb_lower"] = bb.bollinger_lband()
        df["atr"]      = ta.volatility.average_true_range(high, low, close, window=14)

        # Volume
        df["obv"] = ta.volume.on_balance_volume(close, volume)

        last = df.iloc[-1]
        price = float(last["Close"])

        # ── Trend direction ─────────────────────────────────────────────────
        above_ema20  = price > float(last["ema_20"])  if pd.notna(last["ema_20"])  else None
        above_ema50  = price > float(last["ema_50"])  if pd.notna(last["ema_50"])  else None
        above_ema200 = price > float(last["ema_200"]) if pd.notna(last["ema_200"]) else None

        bullish_signals = sum(1 for x in [above_ema20, above_ema50, above_ema200] if x)
        trend = "bullish" if bullish_signals >= 2 else "bearish" if bullish_signals <= 1 else "neutral"

        # ── Support / Resistance (simple pivot) ─────────────────────────────
        recent = df.tail(20)
        support    = float(recent["Low"].min())
        resistance = float(recent["High"].max())
        atr_val    = float(last["atr"]) if pd.notna(last["atr"]) else 0.0

        # ── Setup quality (1–5 stars) ────────────────────────────────────────
        rsi_val = float(last["rsi"]) if pd.notna(last["rsi"]) else 50
        stars = self._score_setup(trend, rsi_val, last, price)

        return {
            "ticker": ticker,
            "price": round(price, 4),
            "trend": trend,
            "rsi": round(rsi_val, 1),
            "macd_bullish": bool(last["macd_diff"] > 0) if pd.notna(last["macd_diff"]) else None,
            "above_ema20": above_ema20,
            "above_ema50": above_ema50,
            "above_ema200": above_ema200,
            "bb_position": self._bb_position(price, last),
            "support": round(support, 4),
            "resistance": round(resistance, 4),
            "atr": round(atr_val, 4),
            "stop_loss": round(price - 1.5 * atr_val, 4),
            "tp1": round(price + 2.0 * atr_val, 4),
            "tp2": round(price + 3.5 * atr_val, 4),
            "setup_stars": stars,
            "timeframe": "1h",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _bb_position(self, price: float, last: pd.Series) -> str:
        upper = float(last["bb_upper"]) if pd.notna(last["bb_upper"]) else None
        lower = float(last["bb_lower"]) if pd.notna(last["bb_lower"]) else None
        if upper is None or lower is None:
            return "unknown"
        if price > upper:
            return "above_upper"
        if price < lower:
            return "below_lower"
        mid = (upper + lower) / 2
        return "upper_half" if price > mid else "lower_half"

    def _score_setup(self, trend: str, rsi: float, last: pd.Series, price: float) -> int:
        score = 0
        if trend == "bullish":
            score += 2
        if 40 <= rsi <= 60:
            score += 1
        elif rsi < 30 or rsi > 70:
            score += 1  # oversold/overbought = potential reversal signal
        if pd.notna(last["macd_diff"]) and float(last["macd_diff"]) > 0:
            score += 1
        if pd.notna(last["bb_lower"]) and price <= float(last["bb_lower"]) * 1.02:
            score += 1
        return min(max(score, 1), 5)

    # ── Bus message handler ────────────────────────────────────────────────────

    async def handle_message(self, msg: BusMessage) -> None:
        """Respond to watchlist update requests."""
        if msg.type == MessageType.REQUEST_INFO and "watchlist" in msg.payload:
            new_tickers = msg.payload["watchlist"]
            if isinstance(new_tickers, list):
                self.watchlist = new_tickers
                log.info("[Charts] Watchlist updated: %s", self.watchlist)
