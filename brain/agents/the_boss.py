"""
The Boss — Final Verdict (Dept 4: Decisión y Riesgo)

The last AI decision-maker before a signal reaches the user.
Receives Shield-approved plans and issues the final verdict:
  STRONG BUY | BUY | SHORT | STRONG SHORT | HOLD | SKIP

Cost-first design:
  - Primary path: rule-based scoring (0 LLM calls)
  - LLM only fires when score is borderline (within 15% of threshold)
  - Uses Haiku (cheapest) when it does call

Scoring model (rule-based, 0-100):
  Conviction from Architect (0-40 pts)
  Pattern Master stars      (0-20 pts)
  Mood Ring alignment       (0-20 pts)
  Bridge regime alignment   (0-10 pts)
  Risk/Reward ratio         (0-10 pts)

Thresholds:
  80-100 → STRONG BUY / STRONG SHORT
  65-79  → BUY / SHORT
  50-64  → borderline → LLM decides (Haiku)
  <50    → SKIP (no LLM call)
"""

import json
import logging
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

BORDERLINE_LOW  = 50
BORDERLINE_HIGH = 65
STRONG_THRESHOLD = 80

BOSS_SYSTEM_PROMPT = """You are The Boss 👔, the final decision-maker at TradingAICenter.
A trade plan has passed risk checks (The Shield) and scored borderline on the scoring model.
Make the final call: approve or skip.

Return ONLY valid JSON (no markdown):
{
  "verdict": "BUY" | "SHORT" | "SKIP",
  "final_conviction": <0.0-1.0>,
  "reason": "<1 sentence — why you decided this>",
  "key_factor": "<the single factor that tipped the decision>"
}
"""


class TheBossAgent(BaseAgent):
    agent_id = "the-boss"
    agent_name = "The Boss"
    department = "decision"
    emoji = "👔"

    def __init__(self) -> None:
        super().__init__()
        # Latest Dept 2 signals for scoring context
        self._mood_score: int = 0          # Mood Ring -100 to +100
        self._bridge_regime: str = "mixed" # The Bridge regime
        self._pattern_stars: dict[str, int] = {}  # ticker → best stars

    async def run_cycle(self) -> None:
        log.debug("[The Boss] Waiting for Shield-approved plans")

    async def handle_message(self, msg: BusMessage) -> None:
        # Shield-approved plan → make final call
        if (msg.category == MessageCategory.TRADE_SIGNAL
                and msg.payload.get("type") == "shield_approved"):
            await self._decide(msg.payload)

        # Track Mood Ring score for scoring
        elif msg.from_agent == "mood-ring" and "score" in msg.payload:
            self._mood_score = int(msg.payload.get("score", 0))

        # Track Bridge regime
        elif msg.from_agent == "the-bridge" and "regime" in msg.payload:
            self._bridge_regime = msg.payload.get("regime", "mixed")

        # Track Pattern Master best stars per ticker
        elif msg.from_agent == "pattern-master":
            for setup in msg.payload.get("setups", []):
                t = setup.get("ticker", "")
                stars = setup.get("stars", 0)
                if t and stars > self._pattern_stars.get(t, 0):
                    self._pattern_stars[t] = stars

    # ── Decision logic ─────────────────────────────────────────────────────────

    async def _decide(self, shield_data: dict) -> None:
        plan = shield_data.get("plan", {})
        risk_summary = shield_data.get("risk_summary", {})
        ticker = plan.get("ticker", "???")

        await self.set_status(AgentStatus.THINKING, f"Final verdict: {ticker}")

        score = self._compute_score(plan)
        direction = plan.get("direction", "long")

        log.info("[The Boss] %s score: %d/100", ticker, score)

        if score >= BORDERLINE_HIGH:
            # Clear signal — rule-based verdict, no LLM
            verdict, conviction = self._score_to_verdict(score, direction)
            reason = f"Rule-based: score {score}/100"
            key_factor = "multi-factor confluence"
        elif score >= BORDERLINE_LOW:
            # Borderline — ask Haiku for final call
            verdict, conviction, reason, key_factor = await self._llm_decide(
                ticker, plan, score, risk_summary
            )
        else:
            # Below threshold — SKIP, no LLM
            verdict = "SKIP"
            conviction = plan.get("conviction", 0.3)
            reason = f"Score {score}/100 below threshold ({BORDERLINE_LOW})"
            key_factor = "insufficient confluence"

        await self.set_status(AgentStatus.SENDING, f"Publishing verdict: {ticker} → {verdict}")
        await self.publish(
            payload={
                "type": "boss_verdict",
                "ticker": ticker,
                "verdict": verdict,
                "final_conviction": conviction,
                "score": score,
                "reason": reason,
                "key_factor": key_factor,
                "plan": plan,
                "risk_summary": risk_summary,
                "whatsapp_message": shield_data.get("whatsapp_message", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.TRADE_SIGNAL,
            msg_type=MessageType.DIRECT_MESSAGE if verdict == "SKIP" else MessageType.BROADCAST,
            to_agent="the-messenger" if verdict != "SKIP" else "all",
            tickers=[ticker],
            confidence=conviction,
            priority=1,
        )

        if verdict != "SKIP":
            log.info("[The Boss] ✅ %s → %s (%.0f%% conviction, score %d)",
                     ticker, verdict, conviction * 100, score)
        else:
            log.info("[The Boss] ⛔ %s → SKIP (score %d/100)", ticker, score)

        await self.set_status(AgentStatus.IDLE)

    def _compute_score(self, plan: dict) -> int:
        ticker = plan.get("ticker", "")
        direction = plan.get("direction", "long")
        conviction = float(plan.get("conviction", 0.5))
        rr = float(plan.get("rr_ratio") or 0)

        # Conviction from Architect (0-40 pts)
        conv_pts = int(conviction * 40)

        # Pattern Master stars (0-20 pts)
        stars = self._pattern_stars.get(ticker, 0)
        star_pts = int(stars / 5 * 20)

        # Mood Ring alignment (0-20 pts)
        mood_aligned = (
            (direction == "long" and self._mood_score > 0)
            or (direction == "short" and self._mood_score < 0)
        )
        mood_strength = abs(self._mood_score) / 100
        mood_pts = int(20 * mood_strength) if mood_aligned else 0

        # Bridge regime alignment (0-10 pts)
        regime_aligned = (
            (direction == "long" and self._bridge_regime == "risk-on")
            or (direction == "short" and self._bridge_regime == "risk-off")
            or self._bridge_regime == "mixed"
        )
        regime_pts = 10 if regime_aligned else 0

        # R:R ratio (0-10 pts): 1.5→3pts, 2.0→6pts, 3.0→10pts
        rr_pts = min(10, int(rr / 3 * 10)) if rr >= 1.5 else 0

        return conv_pts + star_pts + mood_pts + regime_pts + rr_pts

    def _score_to_verdict(self, score: int, direction: str) -> tuple[str, float]:
        is_long = direction == "long"
        if score >= STRONG_THRESHOLD:
            return ("STRONG BUY" if is_long else "STRONG SHORT"), min(0.95, score / 100)
        return ("BUY" if is_long else "SHORT"), score / 100

    async def _llm_decide(
        self, ticker: str, plan: dict, score: int, risk_summary: dict
    ) -> tuple[str, float, str, str]:
        """Haiku call for borderline cases only."""
        context = (
            f"Ticker: {ticker} | Direction: {plan.get('direction')} | Score: {score}/100\n"
            f"Conviction: {plan.get('conviction', 0):.2f} | R:R: {plan.get('rr_ratio', 0)}\n"
            f"Mood Ring: {self._mood_score} | Bridge regime: {self._bridge_regime}\n"
            f"Risk profile: {settings.risk_profile} | Pre-event: {risk_summary.get('pre_event', False)}\n"
            f"Eleventh Man counter: {plan.get('eleventh_man', 'N/A')}"
        )
        try:
            raw = await self.ask_claude(
                system=BOSS_SYSTEM_PROMPT,
                user=context,
                model=settings.analysis_model,  # Haiku — cheapest
                max_tokens=150,
                temperature=0.2,
            )
            result = json.loads(raw)
            verdict = result.get("verdict", "SKIP")
            # Map to directional verdicts
            if verdict == "BUY" and plan.get("direction") == "short":
                verdict = "SHORT"
            return (
                verdict,
                float(result.get("final_conviction", 0.5)),
                result.get("reason", "LLM borderline decision"),
                result.get("key_factor", "borderline score"),
            )
        except Exception as exc:
            log.warning("[The Boss] LLM fallback failed for %s: %s → SKIP", ticker, exc)
            return "SKIP", 0.4, "LLM call failed — defaulting to SKIP", "system error"
