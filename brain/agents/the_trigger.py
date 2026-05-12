"""
The Trigger — Trade Executor (Dept 5: Ejecución)

Executes trades ONLY after explicit human approval arrives from The Messenger.
Places orders via Alpaca paper trading (LIVE_TRADING=false always enforced at startup).

On execution:
  1. Validates LIVE_TRADING=false (hard stop if true — never executes live)
  2. Places market/limit order via Alpaca paper API
  3. Places stop-loss order immediately after fill
  4. Publishes trade_executed → Watchdog starts monitoring
  5. Publishes trade_closed (on Watchdog close signal) → Shield frees slot

On close signal from Watchdog:
  - Closes position at market
  - Publishes trade_closed with final P&L

Zero LLM calls. Pure order management.
"""

import logging
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)


class TheTriggerAgent(BaseAgent):
    agent_id = "the-trigger"
    agent_name = "The Trigger"
    department = "execution"
    emoji = "⚡"

    def __init__(self) -> None:
        super().__init__()
        self._alpaca = None   # lazy-init
        self._open_orders: dict[str, dict] = {}  # ticker → order info

    async def run_cycle(self) -> None:
        log.debug("[The Trigger] Open orders: %d | Live trading: %s",
                  len(self._open_orders), settings.live_trading)

    async def handle_message(self, msg: BusMessage) -> None:
        # Approved by user → execute
        if (msg.category == MessageCategory.TRADE_SIGNAL
                and msg.payload.get("type") == "trade_approved"):
            await self._execute(msg.payload)

        # Close signal from Watchdog → exit position
        elif (msg.category == MessageCategory.RISK
              and msg.payload.get("type") in {"stop_hit", "tp_hit", "forced_close", "flash_crash"}
              and msg.to_agent == self.agent_id):
            await self._close_position(msg.payload)

    # ── Execution ─────────────────────────────────────────────────────────────

    async def _execute(self, approval_data: dict) -> None:
        ticker = approval_data.get("ticker", "???")
        plan = approval_data.get("plan", {})
        size_modifier = float(approval_data.get("size_modifier", 1.0))

        # Hard safety check — NEVER execute live trades
        if settings.live_trading:
            log.error("[The Trigger] 🚫 LIVE_TRADING=true detected — refusing to execute. "
                      "Set LIVE_TRADING=false and restart.")
            return

        await self.set_status(AgentStatus.WORKING, f"Executing: {ticker}")

        direction = plan.get("direction", "long")
        entry = plan.get("entry")
        stop = plan.get("stop")
        risk_pct = float(plan.get("risk_pct", settings.risk_pct_per_trade))

        # Size calculation based on risk %
        account_value = await self._get_account_value()
        risk_dollars = account_value * (risk_pct / 100) * size_modifier
        if entry and stop and abs(entry - stop) > 0:
            qty = max(1, int(risk_dollars / abs(entry - stop)))
        else:
            qty = 1

        order_result = await self._place_order(ticker, direction, qty, entry, stop)

        if order_result:
            self._open_orders[ticker] = {
                "order_id": order_result.get("id", "paper"),
                "qty": qty,
                "direction": direction,
                "plan": plan,
            }
            await self.set_status(AgentStatus.SENDING, f"Broadcasting execution: {ticker}")
            await self.publish(
                payload={
                    "type": "trade_executed",
                    "ticker": ticker,
                    "direction": direction,
                    "qty": qty,
                    "plan": plan,
                    "size_modifier": size_modifier,
                    "risk_pct": risk_pct,
                    "account_value": account_value,
                    "paper_trading": True,
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                },
                category=MessageCategory.TRADE_SIGNAL,
                msg_type=MessageType.BROADCAST,
                tickers=[ticker],
                priority=1,
            )
            log.info("[The Trigger] ⚡ Executed %s %s×%d | paper mode",
                     direction.upper(), ticker, qty)
        else:
            log.error("[The Trigger] Order failed for %s", ticker)

        await self.set_status(AgentStatus.IDLE)

    async def _close_position(self, close_data: dict) -> None:
        ticker = close_data.get("ticker", "")
        close_type = close_data.get("type", "unknown")
        price = close_data.get("price", 0.0)
        pnl_pct = close_data.get("pnl_pct", 0.0)

        order_info = self._open_orders.pop(ticker, None)
        if not order_info:
            log.warning("[The Trigger] Close signal for untracked position: %s", ticker)
            return

        await self.set_status(AgentStatus.WORKING, f"Closing: {ticker}")

        await self._place_close(ticker, order_info["direction"], order_info["qty"])

        # Determine P&L label
        result = "WIN" if pnl_pct > 0 else "LOSS" if pnl_pct < 0 else "BREAK EVEN"

        await self.publish(
            payload={
                "trade_closed": True,
                "type": "trade_closed",
                "ticker": ticker,
                "close_type": close_type,
                "exit_price": price,
                "pnl_pct": pnl_pct,
                "result": result,
                "plan": order_info["plan"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.RISK,
            msg_type=MessageType.BROADCAST,
            tickers=[ticker],
            priority=2,
        )

        icon = "✅" if pnl_pct > 0 else "❌"
        log.info("[The Trigger] %s Closed %s | %s | P&L: %.2f%%", icon, ticker, close_type, pnl_pct)
        await self.set_status(AgentStatus.IDLE)

    # ── Alpaca paper API ──────────────────────────────────────────────────────

    def _get_alpaca(self):
        if self._alpaca is None:
            if not settings.alpaca_api_key:
                return None
            try:
                from alpaca.trading.client import TradingClient
                self._alpaca = TradingClient(
                    api_key=settings.alpaca_api_key,
                    secret_key=settings.alpaca_secret_key,
                    paper=True,   # Always paper — mirrors LIVE_TRADING=false
                )
            except ImportError:
                log.warning("[The Trigger] alpaca-py not installed — using simulated mode")
        return self._alpaca

    async def _get_account_value(self) -> float:
        client = self._get_alpaca()
        if not client:
            return 10_000.0  # Default paper portfolio assumption
        import asyncio
        loop = asyncio.get_event_loop()
        try:
            account = await loop.run_in_executor(None, client.get_account)
            return float(account.portfolio_value)
        except Exception:
            return 10_000.0

    async def _place_order(self, ticker: str, direction: str,
                           qty: int, entry: float | None, stop: float | None) -> dict | None:
        client = self._get_alpaca()
        if not client:
            # Simulated mode — pretend order filled
            log.info("[The Trigger] 📋 SIMULATED order: %s %s×%d (no Alpaca key)", direction, ticker, qty)
            return {"id": "simulated", "status": "filled", "qty": qty}

        import asyncio
        loop = asyncio.get_event_loop()
        try:
            from alpaca.trading.requests import MarketOrderRequest, StopOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            side = OrderSide.BUY if direction == "long" else OrderSide.SELL

            # Market order for entry
            order_req = MarketOrderRequest(
                symbol=ticker,
                qty=qty,
                side=side,
                time_in_force=TimeInForce.DAY,
            )
            order = await loop.run_in_executor(None, client.submit_order, order_req)

            # Stop-loss order immediately after
            if stop:
                stop_side = OrderSide.SELL if direction == "long" else OrderSide.BUY
                stop_req = StopOrderRequest(
                    symbol=ticker,
                    qty=qty,
                    side=stop_side,
                    time_in_force=TimeInForce.GTC,
                    stop_price=round(stop, 2),
                )
                await loop.run_in_executor(None, client.submit_order, stop_req)

            return {"id": str(order.id), "status": order.status, "qty": qty}

        except Exception as exc:
            log.error("[The Trigger] Alpaca order failed for %s: %s", ticker, exc)
            return None

    async def _place_close(self, ticker: str, direction: str, qty: int) -> None:
        client = self._get_alpaca()
        if not client:
            log.info("[The Trigger] 📋 SIMULATED close: %s×%d", ticker, qty)
            return
        import asyncio
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, client.close_position, ticker)
        except Exception as exc:
            log.error("[The Trigger] Close position failed for %s: %s", ticker, exc)
