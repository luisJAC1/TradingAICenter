"""
Globe — Forex, Macro & Geopolitical Economy (Dept 1: Investigación)

Tracks global money flows, DXY, major forex pairs, Treasury yields,
and macro regime (Risk-On / Risk-Off / Stagflation / Reflation).

Data sources (all free, no key required):
- yfinance for DXY, forex pairs, Treasury yields, gold, oil, VIX
"""

import logging
from datetime import datetime, timezone

import pandas as pd

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from market.market_data import fetch_bars_multiindex

log = logging.getLogger(__name__)

# Key macro instruments via yfinance
MACRO_TICKERS = {
    "DXY":     "DX-Y.NYB",    # US Dollar Index
    "GOLD":    "GC=F",         # Gold futures
    "OIL":     "CL=F",         # Crude oil futures
    "VIX":     "^VIX",         # Volatility index
    "US10Y":   "^TNX",         # 10-year Treasury yield
    "US2Y":    "^IRX",         # 2-year Treasury yield (proxy)
    "SPY":     "SPY",           # S&P 500 proxy
}

FOREX_PAIRS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "USDCAD": "CAD=X",
    "AUDUSD": "AUDUSD=X",
    "USDMXN": "MXN=X",
}


class GlobeAgent(BaseAgent):
    agent_id = "globe"
    agent_name = "Globe"
    department = "research"
    emoji = "🌍"

    async def run_cycle(self) -> None:
        await self.set_status(AgentStatus.WORKING, "Reading global macro landscape")

        macro = self._fetch_macro()
        forex = self._fetch_forex()

        if not macro:
            await self.set_status(AgentStatus.IDLE)
            return

        regime = self._determine_regime(macro)
        signals = self._generate_signals(macro, forex, regime)

        await self.set_status(AgentStatus.SENDING, "Publishing macro intelligence")
        await self.publish(
            payload={
                "macro": macro,
                "forex": forex,
                "regime": regime,
                "signals": signals,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.MACRO,
            markets=["forex", "stocks", "crypto", "commodities"],
            confidence=0.72,
            priority=4,
        )
        log.info("[Globe] Regime: %s | DXY: %s | VIX: %s",
                 regime["name"],
                 macro.get("DXY", {}).get("price", "?"),
                 macro.get("VIX", {}).get("price", "?"))

        await self.set_status(AgentStatus.IDLE)

    # ── Data fetchers ──────────────────────────────────────────────────────────

    def _fetch_macro(self) -> dict:
        tickers = list(MACRO_TICKERS.values())
        names   = list(MACRO_TICKERS.keys())
        try:
            df_all = fetch_bars_multiindex(tickers, timeframe="1d", period="30d")
        except Exception as exc:
            log.debug("[Globe] Batch macro fetch failed: %s", exc)
            df_all = pd.DataFrame()

        result = {}
        # Yield ETFs (IEF, SHY) are inverse to yields — flip their changes
        yield_inverse_names = {"US10Y", "US2Y"}

        for name, ticker in zip(names, tickers):
            try:
                if isinstance(df_all.columns, pd.MultiIndex):
                    if ticker not in df_all.columns.get_level_values(0):
                        continue
                    df = df_all[ticker].copy()
                else:
                    df = df_all.copy()
                closes = df["Close"].dropna()
                if len(closes) < 2:
                    continue
                price = float(closes.iloc[-1])
                prev  = float(closes.iloc[-2])
                first = float(closes.iloc[0])
                ch_1d = (price / prev - 1) * 100
                ch_5d = (price / first - 1) * 100
                if name in yield_inverse_names:
                    # ETF price up = yields down. Invert so semantics match.
                    ch_1d, ch_5d = -ch_1d, -ch_5d
                result[name] = {
                    "price": round(price, 4),
                    "change_1d_pct": round(ch_1d, 2),
                    "change_5d_pct": round(ch_5d, 2),
                }
            except Exception as exc:
                log.debug("[Globe] Failed to parse %s (%s): %s", name, ticker, exc)
        return result

    def _fetch_forex(self) -> dict:
        tickers = list(FOREX_PAIRS.values())
        pairs   = list(FOREX_PAIRS.keys())
        try:
            df_all = fetch_bars_multiindex(tickers, timeframe="1d", period="30d")
        except Exception as exc:
            log.debug("[Globe] Batch forex fetch failed: %s", exc)
            df_all = pd.DataFrame()

        result = {}
        for pair, ticker in zip(pairs, tickers):
            try:
                if isinstance(df_all.columns, pd.MultiIndex):
                    if ticker not in df_all.columns.get_level_values(0):
                        continue
                    df = df_all[ticker].copy()
                else:
                    df = df_all.copy()
                closes = df["Close"].dropna()
                if len(closes) < 2:
                    continue
                price = float(closes.iloc[-1])
                prev  = float(closes.iloc[-2])
                result[pair] = {
                    "rate": round(price, 5),
                    "change_1d_pct": round((price / prev - 1) * 100, 3),
                }
            except Exception as exc:
                log.debug("[Globe] Failed to fetch forex %s: %s", pair, exc)
        return result

    # ── Macro regime ───────────────────────────────────────────────────────────

    def _determine_regime(self, macro: dict) -> dict:
        """
        Classify the macro regime based on DXY, VIX, yields, and gold.
        Risk-On: low VIX, weak DXY, rising SPY
        Risk-Off: high VIX, strong DXY, falling SPY
        Stagflation: rising oil + yields, weak SPY
        Reflation: rising yields + SPY, weak DXY
        """
        vix   = macro.get("VIX",   {}).get("price", 20)
        dxy   = macro.get("DXY",   {}).get("change_5d_pct", 0)
        spy   = macro.get("SPY",   {}).get("change_5d_pct", 0)
        oil   = macro.get("OIL",   {}).get("change_5d_pct", 0)
        us10y = macro.get("US10Y", {}).get("change_5d_pct", 0)

        if vix < 18 and spy > 0 and dxy < 0:
            name, description = "RISK_ON", "Low volatility, equities rising, dollar weakening"
        elif vix > 25 or spy < -2:
            name, description = "RISK_OFF", "Elevated fear, capital flight to safety"
        elif oil > 3 and us10y > 2:
            name, description = "STAGFLATION", "Rising commodity prices and yields — growth concerns"
        elif us10y > 1 and spy > 0:
            name, description = "REFLATION", "Rising yields with growth — economy heating up"
        else:
            name, description = "NEUTRAL", "Mixed signals — no dominant macro regime"

        return {
            "name": name,
            "description": description,
            "vix": vix,
            "dxy_5d_pct": dxy,
            "spy_5d_pct": spy,
        }

    def _generate_signals(self, macro: dict, forex: dict, regime: dict) -> list[dict]:
        signals = []

        # High VIX warning
        vix = macro.get("VIX", {}).get("price", 20)
        if vix > 30:
            signals.append({
                "type": "volatility",
                "signal": "HIGH_VIX",
                "detail": f"VIX at {vix:.1f} — extreme market fear. Reduce position sizes.",
                "strength": "strong",
            })
        elif vix > 20:
            signals.append({
                "type": "volatility",
                "signal": "ELEVATED_VIX",
                "detail": f"VIX at {vix:.1f} — above average, use caution.",
                "strength": "moderate",
            })

        # DXY momentum
        dxy_change = macro.get("DXY", {}).get("change_5d_pct", 0)
        if abs(dxy_change) > 1.5:
            direction = "strengthening" if dxy_change > 0 else "weakening"
            effect = "bearish for commodities & crypto" if dxy_change > 0 else "bullish for commodities & crypto"
            signals.append({
                "type": "forex",
                "signal": f"DXY_{direction.upper()}",
                "detail": f"DXY moved {dxy_change:+.1f}% in 5 days — {effect}",
                "strength": "strong" if abs(dxy_change) > 2.5 else "moderate",
            })

        # Yield curve
        us10y_price = macro.get("US10Y", {}).get("price")
        if us10y_price and us10y_price > 4.5:
            signals.append({
                "type": "rates",
                "signal": "HIGH_YIELDS",
                "detail": f"10Y Treasury at {us10y_price:.2f}% — headwind for growth stocks",
                "strength": "moderate",
            })

        return signals

    async def handle_message(self, msg: BusMessage) -> None:
        if msg.type == MessageType.REQUEST_INFO and msg.payload.get("request") == "macro_update":
            await self.run_cycle()
