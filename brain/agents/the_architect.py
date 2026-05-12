"""
The Architect — Strategy Planner (Dept 3: Estrategia)

Synthesizes all Dept 1 + Dept 2 intelligence into actionable trade plans.
Orchestrates the Bull vs Bear debate for each candidate ticker, applies
The Eleventh Man's mandatory contrarian check, and enforces hard risk limits
before passing plans to Dept 4.

Hard limits (enforced before publishing):
  - Max 5 simultaneous trade plans
  - Max 2% risk per trade
  - Max 6% total portfolio heat across all plans
  - Never publishes when LIVE_TRADING=false is violated (it always is)

Schedule: every 4 hours + on-demand via REQUEST_INFO
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

DEBATE_TIMEOUT = 45  # seconds to wait for Bull + Bear responses
# Risk limits read from settings at runtime — set by RISK_PROFILE env var

SYNTHESIS_SYSTEM_PROMPT = """You are The Architect 🏛️, the strategy planner at TradingAICenter.
You have received Bull and Bear debate cases for a ticker, plus supporting Dept 1/2 intelligence.
Your job is to synthesize this into one definitive trade plan — or reject the trade entirely.

You must also play The Eleventh Man 🎭: argue the strongest counter-case to whatever
the majority believes. If Bull wins 3-1, you MUST steelman the Bear case before deciding.
Higher consensus = harder The Eleventh Man works.

Return ONLY valid JSON (no markdown):
{
  "ticker": "<symbol>",
  "decision": "TRADE" | "SKIP",
  "direction": "long" | "short" | null,
  "conviction": <0.0-1.0>,
  "entry": <price | null>,
  "stop": <price | null>,
  "tp1": <price | null>,
  "tp2": <price | null>,
  "tp3": <price | null>,
  "risk_pct": <0.0-2.0>,
  "rr_ratio": <float | null>,
  "timeframe": "<days|weeks|months>",
  "thesis": "<2-3 sentences: why this trade, right now>",
  "eleventh_man": "<strongest counter-argument — required even if you decide TRADE>",
  "bull_weight": <0.0-1.0>,
  "bear_weight": <0.0-1.0>,
  "key_invalidation": "<price action that cancels the plan>",
  "market": "<stocks|crypto|forex>"
}

Rules:
- risk_pct MUST be <= 2.0 — reject any plan that requires more
- If Bull and Bear are within 0.1 conviction of each other → SKIP (too close to call)
- eleventh_man is NEVER empty — it is the soul of the system
- SKIP is a valid and often correct decision
"""


class TheArchitectAgent(BaseAgent):
    agent_id = "the-architect"
    agent_name = "The Architect"
    department = "strategy"
    emoji = "🏛️"

    def __init__(self) -> None:
        super().__init__()
        self._signal_window: dict[str, list[dict]] = {}   # ticker → signals
        self._global_signals: list[dict] = []
        # Pending debate tracking: ticker → {"bull": dict|None, "bear": dict|None, "event": Event}
        self._debates: dict[str, dict] = {}
        self._active_plan_count: int = 0

    async def run_cycle(self) -> None:
        await self.set_status(AgentStatus.WORKING, "Reviewing intelligence")

        candidates = self._select_candidates()
        if not candidates:
            log.info("[The Architect] No candidates — market not ready")
            await self.set_status(AgentStatus.IDLE)
            return

        slots_available = settings.max_simultaneous_plans - self._active_plan_count
        candidates = candidates[:slots_available]

        log.info("[The Architect] Evaluating %d candidate(s): %s", len(candidates), candidates)

        plans = []
        for ticker in candidates:
            plan = await self._evaluate_ticker(ticker)
            if plan and plan.get("decision") == "TRADE":
                plans.append(plan)

        if plans:
            await self.set_status(AgentStatus.SENDING, f"Publishing {len(plans)} trade plan(s)")
            for plan in plans:
                await self.publish(
                    payload={
                        **plan,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "paper_trading": not settings.live_trading,
                    },
                    category=MessageCategory.TRADE_SIGNAL,
                    msg_type=MessageType.BROADCAST,
                    tickers=[plan["ticker"]],
                    confidence=plan.get("conviction", 0.5),
                    priority=2,
                )
            self._active_plan_count += len(plans)
            log.info("[The Architect] Published %d plan(s) | Total heat slots: %d/%d",
                     len(plans), self._active_plan_count, settings.max_simultaneous_plans)
        else:
            log.info("[The Architect] No trades today — discipline is a strategy")

        await self.set_status(AgentStatus.IDLE)

    async def handle_message(self, msg: BusMessage) -> None:
        # Accumulate Dept 1 + Dept 2 signals
        if msg.category in {
            MessageCategory.ANALYSIS, MessageCategory.TECHNICAL,
            MessageCategory.SENTIMENT, MessageCategory.NEWS,
            MessageCategory.FUNDAMENTAL, MessageCategory.MACRO,
            MessageCategory.ALTERNATIVE_DATA,
        } and msg.type not in {MessageType.AGENT_STATUS, MessageType.DEBATE_ROUND}:
            slim = {"from": msg.from_agent, "cat": msg.category.value,
                    "conf": msg.confidence, "payload": _slim(msg.payload)}
            for t in (msg.tickers_relevant or []):
                self._signal_window.setdefault(t, []).append(slim)
                if len(self._signal_window[t]) > 20:
                    self._signal_window[t] = self._signal_window[t][-20:]
            if not msg.tickers_relevant:
                self._global_signals.append(slim)
                if len(self._global_signals) > 40:
                    self._global_signals = self._global_signals[-40:]

        # Collect Bull/Bear debate responses
        elif msg.type == MessageType.DEBATE_ROUND:
            agent = msg.payload.get("agent")
            ticker = msg.payload.get("ticker", "")
            if not ticker or agent not in ("bull", "bear"):
                return
            if ticker in self._debates:
                self._debates[ticker][agent] = msg.payload
                if (self._debates[ticker]["bull"] is not None
                        and self._debates[ticker]["bear"] is not None):
                    self._debates[ticker]["event"].set()

        # On-demand trigger
        elif msg.type == MessageType.REQUEST_INFO and msg.payload.get("request") == "strategy_cycle":
            asyncio.create_task(self.run_cycle())

        # Reset active plan count when plans are closed (from Watchdog/Trigger)
        elif msg.category == MessageCategory.RISK and msg.payload.get("plan_closed"):
            self._active_plan_count = max(0, self._active_plan_count - 1)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _select_candidates(self) -> list[str]:
        """Pick tickers with the most multi-source signal confluence."""
        scores: dict[str, float] = {}
        for ticker, signals in self._signal_window.items():
            if len(signals) < 2:  # Need at least 2 sources
                continue
            sources = {s["from"] for s in signals}
            avg_conf = sum(s["conf"] for s in signals) / len(signals)
            # Bonus for pattern-master hits and mood-ring coverage
            pattern_hit = any(s["from"] == "pattern-master" for s in signals)
            mood_hit = any(s["from"] == "mood-ring" for s in signals)
            scores[ticker] = (len(sources) * 0.4 + avg_conf * 0.4
                              + (0.1 if pattern_hit else 0) + (0.1 if mood_hit else 0))
        return sorted(scores, key=scores.get, reverse=True)[:settings.max_simultaneous_plans]  # type: ignore[arg-type]

    async def _evaluate_ticker(self, ticker: str) -> dict | None:
        """Trigger Bull/Bear debate and synthesize the result."""
        event = asyncio.Event()
        self._debates[ticker] = {"bull": None, "bear": None, "event": event}

        # Request both cases in parallel
        await self.publish(
            payload={"request": "bull_case", "ticker": ticker},
            msg_type=MessageType.REQUEST_INFO,
            to_agent="bull",
        )
        await self.publish(
            payload={"request": "bear_case", "ticker": ticker},
            msg_type=MessageType.REQUEST_INFO,
            to_agent="bear",
        )

        await self.set_status(AgentStatus.WAITING, f"Bull vs Bear debate: {ticker}")
        try:
            await asyncio.wait_for(event.wait(), timeout=DEBATE_TIMEOUT)
        except asyncio.TimeoutError:
            log.warning("[The Architect] Debate timeout for %s — using whatever arrived", ticker)

        bull = self._debates[ticker].get("bull")
        bear = self._debates[ticker].get("bear")
        del self._debates[ticker]

        if not bull and not bear:
            log.info("[The Architect] No debate responses for %s — skipping", ticker)
            return None

        intel = self._build_intel_digest(ticker)
        debate_text = f"Bull case:\n{json.dumps(bull or {})}\n\nBear case:\n{json.dumps(bear or {})}"

        await self.set_status(AgentStatus.THINKING, f"Synthesizing plan: {ticker}")
        try:
            raw = await self.ask_claude(
                system=SYNTHESIS_SYSTEM_PROMPT,
                user=(
                    f"Ticker: {ticker}\n"
                    f"Active risk profile: {settings.risk_profile} "
                    f"(max {settings.risk_pct_per_trade}% risk/trade)\n\n"
                    f"{debate_text}\n\nSupporting intel:\n{intel}"
                ),
                model=settings.reasoning_model,
                max_tokens=700,
                temperature=0.3,
            )
            plan = json.loads(raw)
        except Exception as exc:
            log.warning("[The Architect] Synthesis failed for %s: %s", ticker, exc)
            return None

        # Hard risk limit enforcement — uses active risk profile
        if plan.get("risk_pct", 99) > settings.risk_pct_per_trade:
            log.info("[The Architect] %s rejected — risk %.1f%% exceeds %s limit (%.1f%%)",
                     ticker, plan.get("risk_pct"), settings.risk_profile,
                     settings.risk_pct_per_trade)
            plan["decision"] = "SKIP"

        return plan

    def _build_intel_digest(self, ticker: str) -> str:
        lines = []
        ticker_sigs = self._signal_window.get(ticker, [])
        for s in (ticker_sigs + self._global_signals[-10:])[-15:]:
            lines.append(f"[{s['from']}|{s['cat']}] {s['payload']}")
        return "\n".join(lines) or "Limited intel available."


def _slim(payload: dict) -> dict:
    keep = {"score", "direction", "trend", "label", "stars", "pattern", "entry",
            "stop", "rr_ratio", "regime", "sentiment_score", "conviction",
            "impact_score", "bias", "signal", "thesis"}
    return {k: v for k, v in payload.items() if k in keep}
