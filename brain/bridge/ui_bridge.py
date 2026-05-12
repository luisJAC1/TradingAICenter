"""
UI Bridge — Forwards Knowledge Bus messages to Claw-Empire UI.

When an agent publishes a status update or analysis, this bridge
calls the Claw-Empire REST API so the pixel office reflects it in real time.

Claw-Empire does not have a direct Redis connection — the Brain pushes updates
via HTTP so the UI stays decoupled from the Python infrastructure.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from config import settings
from knowledge_bus.bus import bus, BusMessage, MessageType, MessageCategory

log = logging.getLogger(__name__)

# Mapping from brain agent_id → Claw-Empire agent status values
STATUS_MAP = {
    "idle":     "idle",
    "working":  "working",
    "thinking": "thinking",
    "sending":  "sending",
    "waiting":  "idle",
    "error":    "idle",
    "paused":   "idle",
}


class UIBridge:
    """
    Subscribes to the Knowledge Bus and forwards relevant events to the
    Claw-Empire UI via its REST API.
    """

    def __init__(self) -> None:
        self._http: httpx.AsyncClient | None = None
        self._ui_base = settings.ui_url.rstrip("/")
        self._token = settings.ui_api_token
        self._connected = False

    async def start(self) -> None:
        self._http = httpx.AsyncClient(timeout=5.0)

        # Subscribe to the bus — bridge listens to everything
        await bus.subscribe("ui-bridge", self._handle)
        log.info("[UIBridge] Listening on Knowledge Bus → forwarding to %s", self._ui_base)

        # Test UI connectivity
        try:
            resp = await self._http.get(
                f"{self._ui_base}/api/health",
                headers=self._auth_headers(),
            )
            self._connected = resp.status_code < 500
            log.info("[UIBridge] Claw-Empire reachable: %s", self._connected)
        except Exception as exc:
            log.warning("[UIBridge] Claw-Empire not reachable yet: %s", exc)
            self._connected = False

    async def stop(self) -> None:
        if self._http:
            await self._http.aclose()

    # ── Bus handler ───────────────────────────────────────────────────────────

    async def _handle(self, msg: BusMessage) -> None:
        if msg.type == MessageType.AGENT_STATUS:
            await self._forward_agent_status(msg)
        elif msg.category == MessageCategory.TRADE_SIGNAL:
            await self._forward_trade_signal(msg)
        elif msg.category in (MessageCategory.TECHNICAL, MessageCategory.NEWS, MessageCategory.MACRO,
                              MessageCategory.ANALYSIS):
            await self._forward_analysis(msg)

    async def _forward_agent_status(self, msg: BusMessage) -> None:
        payload = msg.payload
        agent_id = payload.get("agent_id", msg.from_agent)
        status   = STATUS_MAP.get(payload.get("status", "idle"), "idle")
        task     = payload.get("current_task", "")

        await self._post(
            "/api/brain/agent-status",
            {"agent_id": agent_id, "status": status, "current_task": task},
        )

    async def _forward_trade_signal(self, msg: BusMessage) -> None:
        """Push trade signal to the UI decision inbox."""
        payload = msg.payload
        # Only forward finalized reports from The Scribe (has whatsapp_message)
        if "whatsapp_message" not in payload and "raw_plan" not in payload:
            return
        await self._post(
            "/api/brain/decision-inbox",
            {
                "from_agent": msg.from_agent,
                "ticker": payload.get("ticker", ""),
                "message": payload.get("whatsapp_message", ""),
                "raw_plan": payload.get("raw_plan", payload),
                "confidence": msg.confidence,
                "tickers": msg.tickers_relevant,
                "timestamp": msg.timestamp,
            },
        )
        log.info("[UIBridge] Trade signal → decision inbox: %s", payload.get("ticker", ""))

    async def _forward_analysis(self, msg: BusMessage) -> None:
        await self._post(
            "/api/brain/bus-event",
            {
                "message_id": msg.message_id,
                "from_agent": msg.from_agent,
                "category":   msg.category.value,
                "type":       msg.type.value,
                "tickers":    msg.tickers_relevant,
                "confidence": msg.confidence,
                "summary":    self._summarize(msg.payload),
                "timestamp":  msg.timestamp,
            },
        )

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    async def _post(self, path: str, data: dict[str, Any]) -> None:
        if not self._http:
            return
        try:
            await self._http.post(
                f"{self._ui_base}{path}",
                json=data,
                headers=self._auth_headers(),
            )
        except Exception as exc:
            log.debug("[UIBridge] POST %s failed: %s", path, exc)

    def _auth_headers(self) -> dict[str, str]:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    def _summarize(self, payload: dict[str, Any]) -> str:
        """Extract a short human-readable summary from a payload."""
        if "analysis" in payload:
            tickers = [a.get("ticker", "") for a in payload["analysis"][:3]]
            return f"Technical analysis: {', '.join(tickers)}"
        if "items" in payload:
            count = len(payload["items"])
            return f"{count} news items collected"
        if "total_events_this_week" in payload:
            n = payload.get("total_events_this_week", 0)
            hi = payload.get("high_impact_count", 0)
            return f"{n} events this week, {hi} high-impact"
        return str(payload)[:80]


# Singleton
bridge = UIBridge()
