"""
The Professor — Learning Engine (Dept 6: Aprendizaje)

Runs post-mortem analysis on closed trades and publishes an Agent Leaderboard
showing which agents' signals are actually leading to winning trades.

Reads from The Historian's performance_summary messages.
Uses Haiku for concise post-mortem writeups — called once per week (cheap).

Agent Leaderboard: tracks which agent's signal appeared most in winning vs losing trades.
Over time this informs which agents to weight higher.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

POSTMORTEM_PROMPT = """You are The Professor 🎓, the learning engine at TradingAICenter.
You analyze a batch of closed trades and identify patterns in what worked vs what failed.

Return ONLY valid JSON (no markdown):
{
  "key_lesson": "<the single most important thing this week's trades taught us>",
  "what_worked": "<pattern, condition, or setup that produced wins>",
  "what_failed": "<pattern or condition that led to losses>",
  "agent_insight": "<which agent's signals were most/least reliable this period>",
  "system_suggestion": "<one concrete, actionable change to improve next week>",
  "confidence_in_lesson": <0.0-1.0>
}
Keep it tight — max 3 sentences per field.
"""


class TheProfessorAgent(BaseAgent):
    agent_id = "the-professor"
    agent_name = "The Professor"
    department = "learning"
    emoji = "🎓"

    def __init__(self) -> None:
        super().__init__()
        self._recent_trades: list[dict] = []    # from Historian
        # Leaderboard: agent_id → {"wins": int, "losses": int, "appearances": int}
        self._leaderboard: dict[str, dict] = defaultdict(lambda: {"wins": 0, "losses": 0, "appearances": 0})
        self._throttled: bool = False

    async def run_cycle(self) -> None:
        """Weekly: publish leaderboard + post-mortem."""
        if not self._recent_trades:
            log.debug("[The Professor] No trade data yet")
            return

        await self.set_status(AgentStatus.WORKING, "Publishing agent leaderboard")
        await self._publish_leaderboard()

        # Post-mortem (LLM) — only if not throttled and we have enough data
        if not self._throttled and len(self._recent_trades) >= 3:
            await self._run_postmortem()

        self._recent_trades.clear()
        await self.set_status(AgentStatus.IDLE)

    async def handle_message(self, msg: BusMessage) -> None:
        # Receive performance summary from Historian
        if (msg.from_agent == "the-historian"
                and msg.payload.get("type") == "performance_summary"):
            self._recent_trades.append(msg.payload)

        # Trade closed — update leaderboard from plan data
        elif msg.payload.get("trade_closed"):
            self._update_leaderboard(msg.payload)

        # Tokin throttle
        elif (msg.payload.get("type") == "throttle"
              and msg.payload.get("target") == "the-professor"):
            self._throttled = True
            log.info("[The Professor] Throttled by Tokin")

    def _update_leaderboard(self, close_data: dict) -> None:
        plan = close_data.get("plan", {})
        result = close_data.get("result", "")
        # Agents that contributed signals are tracked in plan["contributing_agents"]
        contributors = plan.get("contributing_agents", [])
        is_win = result == "WIN"

        for agent_id in contributors:
            self._leaderboard[agent_id]["appearances"] += 1
            if is_win:
                self._leaderboard[agent_id]["wins"] += 1
            else:
                self._leaderboard[agent_id]["losses"] += 1

    async def _publish_leaderboard(self) -> None:
        board = []
        for agent_id, stats in self._leaderboard.items():
            appearances = stats["appearances"]
            if appearances == 0:
                continue
            win_rate = stats["wins"] / appearances * 100
            board.append({
                "agent": agent_id,
                "appearances": appearances,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "win_rate_pct": round(win_rate, 1),
            })

        board.sort(key=lambda x: x["win_rate_pct"], reverse=True)

        await self.publish(
            payload={
                "type": "agent_leaderboard",
                "leaderboard": board,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.ANALYSIS,
            priority=5,
        )

        if board:
            top = board[0]
            log.info("[The Professor] 🏆 Top agent: %s (%.0f%% win rate, %d trades)",
                     top["agent"], top["win_rate_pct"], top["appearances"])

    async def _run_postmortem(self) -> None:
        await self.set_status(AgentStatus.THINKING, "Running post-mortem analysis")

        # Summarize recent trades for the prompt
        summary = json.dumps(self._recent_trades[-10:], indent=2)

        try:
            raw = await self.ask_claude(
                system=POSTMORTEM_PROMPT,
                user=f"Analyze these recent closed trades:\n{summary}",
                model=settings.analysis_model,  # Haiku — cheap, runs weekly
                max_tokens=400,
                temperature=0.4,
            )
            result = json.loads(raw)
        except Exception as exc:
            log.warning("[The Professor] Post-mortem failed: %s", exc)
            return

        await self.publish(
            payload={
                "type": "post_mortem",
                **result,
                "trades_analyzed": len(self._recent_trades),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.ANALYSIS,
            priority=5,
        )
        log.info("[The Professor] 📝 Post-mortem: %s", result.get("key_lesson", "")[:80])
