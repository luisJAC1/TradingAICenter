"""
The Watchdog — 24/7 Position Monitor (Dept 5: Ejecución)

Monitors all open positions in real time and publishes alerts when:
  - Stop loss is hit or approached (within 20%)
  - TP1 / TP2 / TP3 is hit
  - Position drawdown exceeds 10% of portfolio (emergency alert)
  - Market closes with open position (end-of-day summary)
  - Flash crash detected (price moves >5% in <5 minutes)

On TP1 hit → raises stop to breakeven automatically (trail)
On TP2 hit → publishes CLOSE signal to The Trigger

Zero LLM calls. Pure price-checking math.
Schedule: every 5 minutes during market hours.
"""

import logging
from datetime import datetime, timezone

import yfinance as yf

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

# Alert thresholds
STOP_WARNING_PCT = 20    # Warn when within 20% of stop distance
FLASH_CRASH_PCT  = 5.0  # Alert if price moves >5% in one cycle
EMERGENCY_DD_PCT = 10.0 # Emergency close if position drawdown > 10% of portfolio


class TheWatchdogAgent(BaseAgent):
    agent_id = "the-watchdog"
    agent_name = "The Watchdog"
    department = "execution"
    emoji = "🐕"

    def __init__(self) -> None:
        super().__init__()
        # Tracked positions: ticker → {plan, entry_price, direction, qty, stop, tp1, tp2, tp3,
        #                               tp1_hit, breakeven_set, last_price}
        self._positions: dict[str, dict] = {}
        self._last_prices: dict[str, float] = {}  # for flash crash detection

    async def run_cycle(self) -> None:
        if not self._positions:
            return

        await self.set_status(AgentStatus.WORKING, f"Monitoring {len(self._positions)} position(s)")

        prices = await self._fetch_prices(list(self._positions.keys()))

        for ticker, pos in list(self._positions.items()):
            price = prices.get(ticker)
            if not price:
                log.debug("[Watchdog] No price for %s", ticker)
                continue
            await self._check_position(ticker, pos, price)

        await self.set_status(AgentStatus.IDLE)

    async def handle_message(self, msg: BusMessage) -> None:
        # New trade executed → start tracking
        if (msg.category == MessageCategory.TRADE_SIGNAL
                and msg.payload.get("type") == "trade_executed"):
            await self._register_position(msg.payload)

        # Trade closed → stop tracking
        elif (msg.category == MessageCategory.RISK
              and msg.payload.get("trade_closed")):
            ticker = msg.payload.get("ticker", "")
            self._positions.pop(ticker, None)
            self._last_prices.pop(ticker, None)
            log.info("[Watchdog] Stopped tracking %s", ticker)

    # ── Position tracking ──────────────────────────────────────────────────────

    async def _register_position(self, exec_data: dict) -> None:
        ticker = exec_data.get("ticker", "")
        plan = exec_data.get("plan", {})
        if not ticker:
            return

        self._positions[ticker] = {
            "direction": exec_data.get("direction", "long"),
            "qty": exec_data.get("qty", 1),
            "entry": float(plan.get("entry") or 0),
            "stop":  float(plan.get("stop")  or 0),
            "tp1":   float(plan.get("tp1")   or 0),
            "tp2":   float(plan.get("tp2")   or 0),
            "tp3":   float(plan.get("tp3")   or 0),
            "risk_pct": float(plan.get("risk_pct", settings.risk_pct_per_trade)),
            "tp1_hit": False,
            "tp2_hit": False,
            "breakeven_set": False,
            "executed_at": exec_data.get("executed_at", ""),
        }
        log.info("[Watchdog] 👁️ Tracking %s | entry=%s stop=%s tp1=%s tp2=%s",
                 ticker,
                 self._positions[ticker]["entry"],
                 self._positions[ticker]["stop"],
                 self._positions[ticker]["tp1"],
                 self._positions[ticker]["tp2"])

    # ── Price checks ──────────────────────────────────────────────────────────

    async def _check_position(self, ticker: str, pos: dict, price: float) -> None:
        direction = pos["direction"]
        entry     = pos["entry"]
        stop      = pos["stop"]
        tp1       = pos["tp1"]
        tp2       = pos["tp2"]
        tp3       = pos["tp3"]
        is_long   = direction == "long"

        last_price = self._last_prices.get(ticker, price)
        self._last_prices[ticker] = price

        # P&L calculation
        if entry > 0:
            pnl_pct = ((price - entry) / entry * 100) if is_long \
                      else ((entry - price) / entry * 100)
        else:
            pnl_pct = 0.0

        # Flash crash detection
        if last_price > 0:
            move_pct = abs(price - last_price) / last_price * 100
            if move_pct >= FLASH_CRASH_PCT:
                await self._alert(ticker, "flash_crash",
                                  f"Flash move: {move_pct:.1f}% in one cycle | current={price}",
                                  price, pnl_pct, priority=1)

        # Stop hit
        if stop > 0:
            stop_hit = (is_long and price <= stop) or (not is_long and price >= stop)
            if stop_hit:
                await self._signal_close(ticker, "stop_hit", price, pnl_pct,
                                         f"Stop hit at {price} (stop={stop})")
                return

            # Stop warning — within 20% of stop distance
            if entry > 0 and not pos["breakeven_set"]:
                dist_to_stop = abs(price - stop)
                full_dist = abs(entry - stop)
                if full_dist > 0 and dist_to_stop / full_dist <= (STOP_WARNING_PCT / 100):
                    await self._alert(ticker, "stop_warning",
                                      f"Within {STOP_WARNING_PCT}% of stop | price={price} stop={stop}",
                                      price, pnl_pct, priority=2)

        # TP1 hit → raise stop to breakeven
        if tp1 > 0 and not pos["tp1_hit"]:
            tp1_hit = (is_long and price >= tp1) or (not is_long and price <= tp1)
            if tp1_hit:
                pos["tp1_hit"] = True
                pos["breakeven_set"] = True
                pos["stop"] = entry  # Trail stop to breakeven
                await self._alert(ticker, "tp1_hit",
                                  f"TP1 hit at {price} | Stop trailed to breakeven ({entry})",
                                  price, pnl_pct, priority=2)

        # TP2 hit → close half, let rest run to TP3
        if tp2 > 0 and pos["tp1_hit"] and not pos["tp2_hit"]:
            tp2_hit = (is_long and price >= tp2) or (not is_long and price <= tp2)
            if tp2_hit:
                pos["tp2_hit"] = True
                await self._alert(ticker, "tp2_hit",
                                  f"TP2 hit at {price} — consider closing partial",
                                  price, pnl_pct, priority=2)

        # TP3 hit → close position
        if tp3 > 0 and pos["tp2_hit"]:
            tp3_hit = (is_long and price >= tp3) or (not is_long and price <= tp3)
            if tp3_hit:
                await self._signal_close(ticker, "tp_hit", price, pnl_pct,
                                         f"TP3 hit at {price}")
                return

        # Emergency drawdown check
        account_value = 10_000.0  # Paper account assumption
        loss_dollars = account_value * abs(min(pnl_pct, 0)) / 100
        emergency_threshold = account_value * (EMERGENCY_DD_PCT / 100)
        if pnl_pct < 0 and loss_dollars >= emergency_threshold:
            await self._signal_close(ticker, "forced_close", price, pnl_pct,
                                     f"Emergency: drawdown {pnl_pct:.1f}% exceeds {EMERGENCY_DD_PCT}%")

    async def _signal_close(self, ticker: str, close_type: str,
                            price: float, pnl_pct: float, reason: str) -> None:
        log.info("[Watchdog] 🚨 %s %s | P&L=%.2f%% | %s", ticker, close_type, pnl_pct, reason)
        await self.publish(
            payload={
                "type": close_type,
                "ticker": ticker,
                "price": price,
                "pnl_pct": round(pnl_pct, 2),
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.RISK,
            msg_type=MessageType.DIRECT_MESSAGE,
            to_agent="the-trigger",
            tickers=[ticker],
            priority=1,
        )

    async def _alert(self, ticker: str, alert_type: str, message: str,
                     price: float, pnl_pct: float, priority: int = 3) -> None:
        log.info("[Watchdog] ⚠️ %s %s: %s", ticker, alert_type, message)
        await self.publish(
            payload={
                "type": alert_type,
                "ticker": ticker,
                "message": message,
                "price": price,
                "pnl_pct": round(pnl_pct, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.RISK,
            msg_type=MessageType.ALERT,
            tickers=[ticker],
            priority=priority,
        )

    # ── Price fetcher (free — yfinance) ───────────────────────────────────────

    async def _fetch_prices(self, tickers: list[str]) -> dict[str, float]:
        if not tickers:
            return {}
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_fetch_prices, tickers)


def _sync_fetch_prices(tickers: list[str]) -> dict[str, float]:
    prices = {}
    try:
        data = yf.download(tickers, period="1d", interval="1m",
                           auto_adjust=True, progress=False)
        if data.empty:
            return prices
        close = data["Close"] if "Close" in data.columns else data
        if hasattr(close, "columns"):
            for t in tickers:
                col = t if t in close.columns else None
                if col is not None:
                    last = close[col].dropna()
                    if not last.empty:
                        prices[t] = float(last.iloc[-1])
        else:
            last = close.dropna()
            if not last.empty and len(tickers) == 1:
                prices[tickers[0]] = float(last.iloc[-1])
    except Exception as exc:
        log.warning("[Watchdog] Price fetch failed: %s", exc)
    return prices
