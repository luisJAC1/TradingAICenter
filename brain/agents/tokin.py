"""
Tokin — Budget Watchdog (Special / Meta)

Tracks every LLM API call made by all agents and enforces the monthly budget.
Has VETO power over all LLM calls — when budget is exhausted it sets the
class-level flag in BaseAgent and all non-exempt agents stop calling Claude.

Exempt from veto: The Shield, The Messenger (safety-critical)

Budget tiers:
  80% of budget → ALERT to UI (warning)
  100% of budget → VETO (all LLM calls blocked)
  Month rollover → veto automatically cleared

Zero LLM calls itself. Pure accounting.
"""

import logging
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)


class TokinAgent(BaseAgent):
    agent_id = "tokin"
    agent_name = "Tokin"
    department = "meta"
    emoji = "💰"

    def __init__(self) -> None:
        super().__init__()
        self._monthly_cost: float = 0.0
        self._call_count: int = 0
        self._current_month: int = datetime.now(timezone.utc).month
        self._veto_active: bool = False
        self._alerted: bool = False  # Prevent alert spam

    async def run_cycle(self) -> None:
        await self._check_month_rollover()
        budget = settings.monthly_llm_budget_usd
        pct = (self._monthly_cost / budget * 100) if budget > 0 else 0

        log.info("[Tokin] 💰 Spend: $%.4f / $%.2f (%.1f%%) | Calls: %d | Veto: %s",
                 self._monthly_cost, budget, pct, self._call_count, self._veto_active)

        await self._publish_status_update(pct)

    async def handle_message(self, msg: BusMessage) -> None:
        # Cost telemetry published by BaseAgent after every ask_claude() call
        if (msg.category == MessageCategory.SYSTEM
                and "cost_usd" in msg.payload):
            cost = float(msg.payload.get("cost_usd", 0))
            agent = msg.payload.get("agent", msg.from_agent)
            model = msg.payload.get("model", "unknown")
            tokens = msg.payload.get("input_tokens", 0) + msg.payload.get("output_tokens", 0)

            self._monthly_cost += cost
            self._call_count += 1

            log.debug("[Tokin] %s used %s (%d tokens, $%.5f) | Total: $%.4f",
                      agent, model, tokens, cost, self._monthly_cost)

            await self._evaluate_budget()

    # ── Budget enforcement ─────────────────────────────────────────────────────

    async def _evaluate_budget(self) -> None:
        budget = settings.monthly_llm_budget_usd
        if budget <= 0:
            return

        pct = self._monthly_cost / budget * 100
        alert_pct = settings.alert_threshold_pct  # default 80%

        # Warning threshold
        if pct >= alert_pct and not self._alerted:
            self._alerted = True
            await self._publish_alert(
                level="warning",
                message=f"LLM spend at {pct:.1f}% of monthly budget "
                        f"(${self._monthly_cost:.3f} / ${budget:.2f}). "
                        f"Maverick throttled. Consider reducing analysis frequency.",
                pct=pct,
            )
            # Throttle Maverick first (as per architecture)
            await self.publish(
                payload={"type": "throttle", "target": "maverick", "reason": f"budget at {pct:.0f}%"},
                category=MessageCategory.SYSTEM,
                msg_type=MessageType.DIRECT_MESSAGE,
                to_agent="maverick",
                priority=2,
            )

        # Hard veto at 100%
        if pct >= 100 and not self._veto_active:
            self._veto_active = True
            BaseAgent.set_llm_veto(True)
            await self._publish_alert(
                level="veto",
                message=f"💸 BUDGET EXHAUSTED — LLM calls blocked for all non-exempt agents. "
                        f"Spent ${self._monthly_cost:.3f} of ${budget:.2f} monthly budget. "
                        f"Resets next month.",
                pct=pct,
            )

    async def _publish_status_update(self, pct: float) -> None:
        await self.publish(
            payload={
                "monthly_cost_usd": round(self._monthly_cost, 4),
                "budget_usd": settings.monthly_llm_budget_usd,
                "pct_used": round(pct, 1),
                "call_count": self._call_count,
                "veto_active": self._veto_active,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.SYSTEM,
            priority=5,
        )

    async def _publish_alert(self, level: str, message: str, pct: float) -> None:
        log.warning("[Tokin] %s: %s", level.upper(), message)
        await self.publish(
            payload={
                "type": f"budget_{level}",
                "level": level,
                "message": message,
                "pct_used": round(pct, 1),
                "cost_usd": round(self._monthly_cost, 4),
                "budget_usd": settings.monthly_llm_budget_usd,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.RISK,
            msg_type=MessageType.ALERT,
            priority=1,
        )

    async def _check_month_rollover(self) -> None:
        now = datetime.now(timezone.utc)
        if now.month != self._current_month:
            log.info("[Tokin] 📅 New month — resetting budget counter")
            self._monthly_cost = 0.0
            self._call_count = 0
            self._alerted = False
            self._current_month = now.month
            if self._veto_active:
                self._veto_active = False
                BaseAgent.set_llm_veto(False)
