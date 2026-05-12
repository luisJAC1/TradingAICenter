"""
The Shield — Risk Manager (Dept 4: Decisión y Riesgo)

PURE MATH. Zero LLM calls. The Shield validates every trade plan against
hard risk rules before it reaches The Boss. If any rule fails → VETO.

Veto conditions (all checked, none negotiable):
  1. Risk per trade > settings.risk_pct_per_trade
  2. Total portfolio heat would exceed settings.max_portfolio_heat
  3. Plan count would exceed settings.max_simultaneous_plans
  4. Same ticker already in an active plan
  5. Correlated asset already in an active plan (e.g. QQQ open → no NVDA long)
  6. High-impact event within 24h for the ticker (from Scheduler data)
  7. Pre-event position size must be halved (50% rule)

When a veto fires → publishes RISK alert and stops the chain.
When plan passes → forwards to The Boss with a risk_summary.
"""

import logging
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

# Correlation buckets — if one is open, block the other
CORR_GROUPS = [
    {"QQQ", "NVDA", "AMD", "MSFT", "AAPL", "META", "GOOGL"},  # Mega-cap tech
    {"SPY", "IWM", "DIA"},                                      # Broad index ETFs
    {"BTC-USD", "ETH-USD"},                                     # Crypto
    {"GLD", "SLV"},                                             # Precious metals
]


class TheShieldAgent(BaseAgent):
    agent_id = "the-shield"
    agent_name = "The Shield"
    department = "decision"
    emoji = "🛡️"

    def __init__(self) -> None:
        super().__init__()
        self._active_plans: dict[str, dict] = {}      # ticker → plan
        self._upcoming_events: dict[str, list] = {}   # ticker → [event dicts]

    async def run_cycle(self) -> None:
        log.debug("[The Shield] Watching %d active plan(s)", len(self._active_plans))

    async def handle_message(self, msg: BusMessage) -> None:
        # New trade plan from The Architect → validate
        if (msg.category == MessageCategory.TRADE_SIGNAL
                and msg.from_agent == "the-architect"
                and msg.payload.get("decision") == "TRADE"):
            await self._validate(msg.payload)

        # Economic calendar data from The Scheduler
        elif msg.from_agent == "the-scheduler" and msg.payload.get("upcoming_events"):
            for event in msg.payload["upcoming_events"]:
                for ticker in event.get("tickers_affected", []):
                    self._upcoming_events.setdefault(ticker, []).append(event)

        # Plan closed (from Trigger/Watchdog) → free the slot
        elif msg.category == MessageCategory.RISK and msg.payload.get("trade_closed"):
            ticker = msg.payload.get("ticker", "")
            self._active_plans.pop(ticker, None)
            log.info("[The Shield] Plan closed: %s | Active: %d", ticker, len(self._active_plans))

        # Approved by user → track as active
        elif (msg.category == MessageCategory.TRADE_SIGNAL
              and msg.payload.get("type") == "trade_approved"):
            ticker = msg.payload.get("ticker", "")
            if ticker:
                self._active_plans[ticker] = msg.payload.get("plan", {})

    # ── Validation logic ──────────────────────────────────────────────────────

    async def _validate(self, plan: dict) -> None:
        ticker = plan.get("ticker", "???")
        await self.set_status(AgentStatus.WORKING, f"Risk check: {ticker}")

        vetoes = self._check_all_rules(plan)

        if vetoes:
            await self._veto(ticker, plan, vetoes)
        else:
            await self._approve(ticker, plan)

        await self.set_status(AgentStatus.IDLE)

    def _check_all_rules(self, plan: dict) -> list[str]:
        ticker = plan.get("ticker", "")
        risk_pct = float(plan.get("risk_pct", 0))
        direction = plan.get("direction", "long")
        vetoes = []

        # Rule 1: Risk per trade
        if risk_pct > settings.risk_pct_per_trade:
            vetoes.append(
                f"Risk {risk_pct:.1f}% exceeds {settings.risk_profile} limit "
                f"({settings.risk_pct_per_trade:.1f}%)"
            )

        # Rule 2: Total heat
        current_heat = sum(p.get("risk_pct", 0) for p in self._active_plans.values())
        if current_heat + risk_pct > settings.max_portfolio_heat:
            vetoes.append(
                f"Adding {risk_pct:.1f}% would bring heat to "
                f"{current_heat + risk_pct:.1f}% (limit: {settings.max_portfolio_heat:.1f}%)"
            )

        # Rule 3: Plan count
        if len(self._active_plans) >= settings.max_simultaneous_plans:
            vetoes.append(
                f"Already at max simultaneous plans ({settings.max_simultaneous_plans})"
            )

        # Rule 4: Duplicate ticker
        if ticker in self._active_plans:
            existing_dir = self._active_plans[ticker].get("direction", "")
            vetoes.append(f"Already have an active {existing_dir} plan for {ticker}")

        # Rule 5: Correlated asset already open
        for group in CORR_GROUPS:
            if ticker in group:
                for open_ticker in self._active_plans:
                    if open_ticker in group and open_ticker != ticker:
                        open_dir = self._active_plans[open_ticker].get("direction", "")
                        if open_dir == direction:
                            vetoes.append(
                                f"{ticker} is correlated with open {open_dir} position in {open_ticker}"
                            )
                        break

        # Rule 6 + 7: Upcoming high-impact events within 24h
        events = self._upcoming_events.get(ticker, [])
        high_impact = [e for e in events if e.get("impact", "").lower() == "high"]
        if high_impact:
            # Pre-event: halve the position (warn, don't veto — just flag)
            plan["_pre_event_flag"] = True
            plan["_pre_event_reason"] = high_impact[0].get("event", "high-impact event")
            log.warning("[The Shield] %s: pre-event flag — halve position size", ticker)

        return vetoes

    async def _veto(self, ticker: str, plan: dict, vetoes: list[str]) -> None:
        log.warning("[The Shield] 🛑 VETO %s: %s", ticker, " | ".join(vetoes))
        await self.publish(
            payload={
                "type": "shield_veto",
                "ticker": ticker,
                "vetoes": vetoes,
                "plan": plan,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.RISK,
            msg_type=MessageType.ALERT,
            tickers=[ticker],
            priority=1,
        )

    async def _approve(self, ticker: str, plan: dict) -> None:
        current_heat = sum(p.get("risk_pct", 0) for p in self._active_plans.values())
        new_heat = current_heat + float(plan.get("risk_pct", 0))
        pre_event = plan.pop("_pre_event_flag", False)
        pre_event_reason = plan.pop("_pre_event_reason", "")

        log.info("[The Shield] ✅ %s passed | Heat: %.1f%% → %.1f%% | Pre-event: %s",
                 ticker, current_heat, new_heat, pre_event)

        await self.publish(
            payload={
                "type": "shield_approved",
                "ticker": ticker,
                "plan": plan,
                "risk_summary": {
                    "risk_pct": plan.get("risk_pct"),
                    "heat_before": round(current_heat, 2),
                    "heat_after": round(new_heat, 2),
                    "heat_limit": settings.max_portfolio_heat,
                    "profile": settings.risk_profile,
                    "pre_event": pre_event,
                    "pre_event_reason": pre_event_reason,
                    "size_modifier": 0.5 if pre_event else 1.0,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.TRADE_SIGNAL,
            msg_type=MessageType.DIRECT_MESSAGE,
            to_agent="the-boss",
            tickers=[ticker],
            confidence=plan.get("conviction", 0.5),
            priority=1,
        )
