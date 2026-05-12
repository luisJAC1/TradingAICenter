"""
The Eleventh Man — Mandatory Contrarian (Special)

Implements the Tenth Man Rule: if everyone agrees, one person MUST disagree.
Sits between The Scribe and The Boss — intercepts approved trade plans and
generates the strongest possible counter-argument before The Boss sees the signal.

The higher the consensus conviction, the harder The Eleventh Man works.
  > 0.85 conviction → deep contrarian analysis (Sonnet)
  0.65–0.85 → standard counter (Haiku)
  < 0.65 → light flag (rule-based, no LLM)

Publishes its counter directly to The Boss as DEBATE_ROUND.
"""

import json
import logging
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

ELEVENTH_MAN_PROMPT = """You are The Eleventh Man 🎭, the mandatory contrarian at TradingAICenter.
Everyone agrees on this trade. YOUR JOB IS TO DISAGREE — or at least surface every possible reason it fails.
The higher the consensus, the harder you must work to find the flaw.

You are not trying to be right. You are trying to prevent groupthink.
Find the blind spot. The timing risk. The hidden correlation. The narrative everyone is ignoring.

Return ONLY valid JSON (no markdown):
{
  "counter_thesis": "<2 sentences — the strongest reason this trade fails>",
  "blind_spot": "<what everyone is ignoring right now>",
  "timing_risk": "<why RIGHT NOW might be the wrong time even if the setup is good>",
  "hidden_correlation": "<an asset or event that could invalidate this trade>",
  "severity": "caution" | "warning" | "serious_concern",
  "should_block": false
}

Rules:
- should_block is almost always false — you raise concerns, The Boss decides
- severity = serious_concern only if you find a genuine showstopper
- Be specific. Vague concerns help no one.
"""


class TheEleventhManAgent(BaseAgent):
    agent_id = "the-eleventh-man"
    agent_name = "The Eleventh Man"
    department = "special"
    emoji = "🎭"

    def __init__(self) -> None:
        super().__init__()
        self._throttled: bool = False

    async def run_cycle(self) -> None:
        log.debug("[The Eleventh Man] Watching for high-conviction consensus")

    async def handle_message(self, msg: BusMessage) -> None:
        # Intercept Shield-approved plans before they reach The Boss
        if (msg.category == MessageCategory.TRADE_SIGNAL
                and msg.payload.get("type") == "shield_approved"):
            await self._challenge(msg.payload)

    async def _challenge(self, shield_data: dict) -> None:
        plan = shield_data.get("plan", {})
        ticker = plan.get("ticker", "???")
        conviction = float(plan.get("conviction", 0.5))

        await self.set_status(AgentStatus.THINKING, f"Challenging: {ticker} ({conviction:.0%})")

        counter = await self._generate_counter(ticker, plan, conviction)

        await self.set_status(AgentStatus.SENDING, f"Publishing counter for {ticker}")
        await self.publish(
            payload={
                "agent": "the-eleventh-man",
                "ticker": ticker,
                "original_conviction": conviction,
                "counter": counter,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.ANALYSIS,
            msg_type=MessageType.DEBATE_ROUND,
            tickers=[ticker],
            confidence=0.5,
            priority=2,
        )

        severity = counter.get("severity", "caution")
        log.info("[The Eleventh Man] 🎭 %s | conviction=%.0f%% | severity=%s",
                 ticker, conviction * 100, severity)
        await self.set_status(AgentStatus.IDLE)

    async def _generate_counter(self, ticker: str, plan: dict, conviction: float) -> dict:
        # Low conviction → simple rule-based flag, no LLM
        if conviction < 0.65:
            return {
                "counter_thesis": f"Conviction below 65% — insufficient edge. "
                                  f"Wait for a cleaner setup on {ticker}.",
                "blind_spot": "Low conviction signals often reflect ambiguous market conditions.",
                "timing_risk": "Entering on a weak signal risks getting stopped out before the move.",
                "hidden_correlation": "Check if broader market direction confirms this setup.",
                "severity": "caution",
                "should_block": False,
            }

        # Throttled (Tokin warning) → Haiku only
        model = settings.analysis_model if (self._throttled or conviction < 0.85) \
                else settings.reasoning_model

        context = (
            f"Ticker: {ticker} | Direction: {plan.get('direction')} | "
            f"Conviction: {conviction:.0%}\n"
            f"Thesis: {plan.get('thesis', 'N/A')}\n"
            f"Eleventh Man in plan: {plan.get('eleventh_man', 'N/A')}\n"
            f"Entry: {plan.get('entry')} | Stop: {plan.get('stop')} | R:R: {plan.get('rr_ratio')}"
        )

        try:
            raw = await self.ask_claude(
                system=ELEVENTH_MAN_PROMPT,
                user=f"Everyone agrees on this {conviction:.0%} conviction trade. Challenge it.\n\n{context}",
                model=model,
                max_tokens=350,
                temperature=0.7,  # Higher temp = more creative dissent
            )
            return json.loads(raw)
        except RuntimeError:
            # Tokin veto — return rule-based counter
            return self._rule_based_counter(ticker, plan)
        except Exception as exc:
            log.warning("[The Eleventh Man] Counter generation failed for %s: %s", ticker, exc)
            return self._rule_based_counter(ticker, plan)

    def _rule_based_counter(self, ticker: str, plan: dict) -> dict:
        direction = plan.get("direction", "long")
        return {
            "counter_thesis": f"High consensus on {ticker} {direction} — "
                              f"crowded trades reverse sharply. Who is on the other side?",
            "blind_spot": "When everyone sees the same setup, the edge disappears.",
            "timing_risk": "Crowded positions unwind fast when they unwind.",
            "hidden_correlation": "Monitor options flow — smart money may already be positioned opposite.",
            "severity": "caution",
            "should_block": False,
        }

    async def handle_message(self, msg: BusMessage) -> None:
        if (msg.category == MessageCategory.TRADE_SIGNAL
                and msg.payload.get("type") == "shield_approved"):
            await self._challenge(msg.payload)
        elif (msg.category == MessageCategory.SYSTEM
              and msg.payload.get("type") == "throttle"
              and msg.payload.get("target") == "the-eleventh-man"):
            self._throttled = True
            log.info("[The Eleventh Man] Throttled by Tokin — switching to Haiku")
