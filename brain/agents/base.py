"""
BaseAgent — Every trading agent inherits from this class.

Handles: Knowledge Bus integration, status updates, LLM calls, logging.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import anthropic

from config import settings
from knowledge_bus.bus import bus, BusMessage, MessageType, MessageCategory

log = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    THINKING = "thinking"
    SENDING = "sending"
    WAITING = "waiting"
    ERROR = "error"
    PAUSED = "paused"


# Agents exempt from Tokin's LLM veto (safety-critical)
_VETO_EXEMPT = {"the-shield", "the-messenger", "ui-bridge"}

# Approximate cost per 1K tokens (input+output blended estimate)
_COST_PER_1K = {
    "claude-haiku-4-5-20251001": 0.001,   # ~$1/1M blended
    "claude-sonnet-4-6":         0.009,   # ~$9/1M blended
    "claude-opus-4-7":           0.045,   # ~$45/1M blended
}


class BaseAgent(ABC):
    """
    Abstract base for all TradingAICenter agents.

    Each agent has:
    - A unique ID matching the Claw-Empire DB (e.g. "charts", "x-ray")
    - A department assignment
    - Knowledge Bus subscription for receiving messages
    - Ability to publish messages and status updates to the bus
    - Optional LLM access (via Anthropic API)
    """

    agent_id: str = ""
    agent_name: str = ""
    department: str = ""
    emoji: str = "🤖"

    # Class-level veto flag — Tokin sets this when budget is exhausted
    _llm_vetoed: bool = False

    def __init__(self) -> None:
        self.status = AgentStatus.IDLE
        self.current_task: str | None = None
        self._llm: anthropic.AsyncAnthropic | None = None
        self._running = False

    @classmethod
    def set_llm_veto(cls, vetoed: bool) -> None:
        cls._llm_vetoed = vetoed
        log.warning("[BaseAgent] LLM veto %s", "ENABLED" if vetoed else "CLEARED")

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Connect to bus and subscribe."""
        self._running = True
        await bus.subscribe(self.agent_id, self._on_bus_message)
        await self._publish_status(AgentStatus.IDLE, "Agent online")
        log.info("[%s] Started", self.agent_name)

    async def stop(self) -> None:
        self._running = False
        await self._publish_status(AgentStatus.PAUSED, "Agent offline")
        log.info("[%s] Stopped", self.agent_name)

    # ── Abstract interface ─────────────────────────────────────────────────────

    @abstractmethod
    async def run_cycle(self) -> None:
        """Main analysis cycle — called by the scheduler."""

    async def handle_message(self, msg: BusMessage) -> None:
        """Override to respond to specific bus messages."""

    # ── Knowledge Bus helpers ──────────────────────────────────────────────────

    async def publish(
        self,
        payload: dict[str, Any],
        *,
        category: MessageCategory = MessageCategory.SYSTEM,
        msg_type: MessageType = MessageType.BROADCAST,
        to_agent: str = "all",
        tickers: list[str] | None = None,
        markets: list[str] | None = None,
        confidence: float = 0.0,
        priority: int = 5,
    ) -> None:
        msg = BusMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            type=msg_type,
            category=category,
            tickers_relevant=tickers or [],
            markets_affected=markets or [],
            payload=payload,
            confidence=confidence,
            priority=priority,
        )
        await bus.publish(msg)

    async def _publish_status(self, status: AgentStatus, task: str = "") -> None:
        self.status = status
        self.current_task = task or None
        await self.publish(
            payload={
                "agent_id": self.agent_id,
                "status": status.value,
                "current_task": task,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.STATUS,
            msg_type=MessageType.AGENT_STATUS,
            priority=1,
        )

    async def set_status(self, status: AgentStatus, task: str = "") -> None:
        await self._publish_status(status, task)

    # ── LLM access ────────────────────────────────────────────────────────────

    @property
    def llm(self) -> anthropic.AsyncAnthropic:
        if self._llm is None:
            self._llm = anthropic.AsyncAnthropic(
                api_key=settings.anthropic_api_key
            )
        return self._llm

    async def ask_claude(
        self,
        system: str,
        user: str,
        *,
        model: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        cache_system: bool = True,
    ) -> str:
        """Send a message to Claude and return the text response.

        cache_system=True adds a cache_control breakpoint on the system prompt,
        saving ~90% on repeated calls with the same system prompt (prompt caching).
        """
        system_block: list | str
        if cache_system:
            system_block = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            system_block = system

        # Tokin veto check — exempt agents always allowed
        if BaseAgent._llm_vetoed and self.agent_id not in _VETO_EXEMPT:
            log.warning("[%s] LLM call blocked by Tokin — budget exhausted", self.agent_name)
            raise RuntimeError("Tokin veto: monthly LLM budget exhausted")

        used_model = model or settings.default_model
        response = await self.llm.messages.create(
            model=used_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_block,
            messages=[{"role": "user", "content": user}],
        )

        # Publish cost telemetry for Tokin to track
        usage = response.usage
        total_tokens = usage.input_tokens + usage.output_tokens
        cost_usd = total_tokens / 1000 * _COST_PER_1K.get(used_model, 0.01)
        await self.publish(
            payload={
                "agent": self.agent_id,
                "model": used_model,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cost_usd": round(cost_usd, 6),
            },
            category=MessageCategory.SYSTEM,
            msg_type=MessageType.BROADCAST,
            priority=9,  # Lowest priority — telemetry only
        )

        text = response.content[0].text  # type: ignore[index]
        text = text.strip()
        # Strip markdown code fences (```json ... ``` or ``` ... ```)
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            fence_end = text.rfind("```")
            if fence_end != -1:
                text = text[:fence_end]
            text = text.strip()
        # If there's a JSON object, extract just the first one to discard trailing text
        if text.startswith("{"):
            depth = 0
            for i, ch in enumerate(text):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        text = text[: i + 1]
                        break
        return text

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _on_bus_message(self, msg: BusMessage) -> None:
        # Ignore own messages
        if msg.from_agent == self.agent_id:
            return
        try:
            await self.handle_message(msg)
        except Exception as exc:
            log.error("[%s] Error handling bus message: %s", self.agent_name, exc)
