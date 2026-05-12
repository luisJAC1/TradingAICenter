"""
The Messenger — Notification Delivery (Dept 4: Decisión y Riesgo)

Delivers Boss-approved trade signals to the user.
Primary channel: UI Decision Inbox (always on — zero extra cost).
Optional channel: WhatsApp via OpenClaw (enabled by NOTIFICATION_CHANNEL=whatsapp|both).

UI delivery is instant via the UIBridge already running.
WhatsApp delivery requires WHATSAPP_PHONE + OpenClaw running on port 18789.

Approval flow:
  User sees signal in UI → clicks APPROVE / REJECT / WAIT 1H / MODIFY SIZE
  UI POSTs decision back to /api/brain/approval → Messenger publishes result
  The Trigger only executes on explicit APPROVE

Auto-cancel: if no response within 2 hours → auto-SKIP (signal expires)
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

APPROVAL_TIMEOUT_SECONDS = 7200  # 2 hours


class TheMessengerAgent(BaseAgent):
    agent_id = "the-messenger"
    agent_name = "The Messenger"
    department = "decision"
    emoji = "📲"

    def __init__(self) -> None:
        super().__init__()
        # Pending approvals: ticker → {"payload": dict, "task": asyncio.Task}
        self._pending: dict[str, dict] = {}

    async def run_cycle(self) -> None:
        log.debug("[The Messenger] Active signals: %d", len(self._pending))

    async def handle_message(self, msg: BusMessage) -> None:
        # Final verdict from The Boss — deliver to user
        if (msg.category == MessageCategory.TRADE_SIGNAL
                and msg.from_agent == "the-boss"
                and msg.payload.get("verdict") in {"STRONG BUY", "BUY", "SHORT", "STRONG SHORT"}):
            await self._deliver(msg.payload)

        # Approval response from UI (forwarded via FastAPI /api/brain/approval)
        elif (msg.type == MessageType.DIRECT_MESSAGE
              and msg.payload.get("type") == "approval_response"):
            await self._handle_approval(msg.payload)

    # ── Delivery ──────────────────────────────────────────────────────────────

    async def _deliver(self, boss_data: dict) -> None:
        ticker = boss_data.get("ticker", "???")
        verdict = boss_data.get("verdict", "BUY")
        message = boss_data.get("whatsapp_message", self._build_fallback(boss_data))

        await self.set_status(AgentStatus.SENDING, f"Delivering signal: {ticker}")

        channel = settings.notification_channel.lower()

        # UI delivery — always attempted (UIBridge handles the actual POST)
        # The signal is already on the bus with TRADE_SIGNAL category;
        # UIBridge._forward_trade_signal() picks it up automatically.
        # We publish an explicit delivery confirmation here.
        await self.publish(
            payload={
                "type": "signal_delivered",
                "ticker": ticker,
                "verdict": verdict,
                "message": message,
                "channels": ["ui"] + (["whatsapp"] if channel in ("whatsapp", "both") else []),
                "awaiting_approval": True,
                "expires_at": _expires_iso(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.TRADE_SIGNAL,
            msg_type=MessageType.BROADCAST,
            tickers=[ticker],
            priority=1,
        )

        # WhatsApp delivery (only if configured)
        if channel in ("whatsapp", "both") and settings.whatsapp_phone:
            await self._send_whatsapp(message, ticker)
        elif channel in ("whatsapp", "both"):
            log.info("[The Messenger] WhatsApp configured but WHATSAPP_PHONE not set — UI only")

        log.info("[The Messenger] Signal delivered for %s | Channel: %s", ticker, channel)

        # Start 2h approval timer
        task = asyncio.create_task(self._approval_timer(ticker, boss_data))
        self._pending[ticker] = {"payload": boss_data, "task": task}

        await self.set_status(AgentStatus.WAITING, f"Awaiting approval: {ticker}")

    async def _handle_approval(self, data: dict) -> None:
        ticker = data.get("ticker", "")
        decision = data.get("decision", "REJECT")  # APPROVE | REJECT | WAIT | MODIFY
        pending = self._pending.pop(ticker, None)

        if not pending:
            log.warning("[The Messenger] Approval for unknown/expired signal: %s", ticker)
            return

        pending["task"].cancel()

        if decision == "APPROVE":
            size_modifier = float(data.get("size_modifier", 1.0))
            await self.publish(
                payload={
                    "type": "trade_approved",
                    "ticker": ticker,
                    "plan": pending["payload"].get("plan", {}),
                    "size_modifier": size_modifier,
                    "approved_at": datetime.now(timezone.utc).isoformat(),
                },
                category=MessageCategory.TRADE_SIGNAL,
                msg_type=MessageType.DIRECT_MESSAGE,
                to_agent="the-trigger",
                tickers=[ticker],
                priority=1,
            )
            log.info("[The Messenger] ✅ %s APPROVED (size ×%.1f) → The Trigger", ticker, size_modifier)

        elif decision == "WAIT":
            delay_hours = int(data.get("delay_hours", 1))
            log.info("[The Messenger] ⏸️ %s snoozed %dh", ticker, delay_hours)
            await asyncio.sleep(delay_hours * 3600)
            # Re-deliver after snooze
            await self._deliver(pending["payload"])

        else:  # REJECT or unknown
            await self._publish_cancelled(ticker, "User rejected")
            log.info("[The Messenger] ❌ %s REJECTED by user", ticker)

        await self.set_status(AgentStatus.IDLE)

    async def _approval_timer(self, ticker: str, boss_data: dict) -> None:
        """Auto-cancel after 2 hours with no response."""
        try:
            await asyncio.sleep(APPROVAL_TIMEOUT_SECONDS)
            if ticker in self._pending:
                del self._pending[ticker]
                await self._publish_cancelled(ticker, "2h approval window expired")
                log.info("[The Messenger] ⏰ %s auto-cancelled — no response in 2h", ticker)
                await self.set_status(AgentStatus.IDLE)
        except asyncio.CancelledError:
            pass  # Normal — approval arrived before timeout

    async def _publish_cancelled(self, ticker: str, reason: str) -> None:
        await self.publish(
            payload={
                "type": "trade_cancelled",
                "ticker": ticker,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.RISK,
            msg_type=MessageType.BROADCAST,
            tickers=[ticker],
            priority=3,
        )

    # ── WhatsApp via OpenClaw ─────────────────────────────────────────────────

    async def _send_whatsapp(self, message: str, ticker: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{settings.openclaw_url}/send",
                    json={"phone": settings.whatsapp_phone, "message": message},
                )
                resp.raise_for_status()
                log.info("[The Messenger] WhatsApp sent for %s", ticker)
        except Exception as exc:
            log.warning("[The Messenger] WhatsApp delivery failed for %s: %s — UI only", ticker, exc)

    def _build_fallback(self, data: dict) -> str:
        plan = data.get("plan", {})
        ticker = data.get("ticker", "???")
        verdict = data.get("verdict", "BUY")
        conv = int(data.get("final_conviction", 0.5) * 100)
        return (
            f"🔔 {ticker} — {verdict} · {conv}% conviction\n"
            f"Entry: {plan.get('entry','?')} | Stop: {plan.get('stop','?')} "
            f"| TP1: {plan.get('tp1','?')}\n"
            f"Risk: {plan.get('risk_pct','?')}% | R:R 1:{plan.get('rr_ratio','?')}\n"
            f"[✅ APPROVE] [❌ REJECT] [📄 REPORT] [✏️ MODIFY SIZE] [⏸️ WAIT 1H]"
        )


def _expires_iso() -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(seconds=APPROVAL_TIMEOUT_SECONDS)).isoformat()
