"""
Maverick — Creative Strategist (Special)

Finds lateral connections and 2nd/3rd-order effects that the structured agents miss.
Not a forecaster — a creative thinker that asks "what if everyone is wrong?"

Examples of Maverick thinking:
  "NVDA earnings miss → crypto miners sell GPUs → ETH hashrate → miner stocks"
  "Fed holds rates → dollar weakens → EM debt rally → copper → Freeport"
  "Hurricane season → energy grid stress → demand for battery storage → PLUG/FCEL"

Throttled first when Tokin raises budget alerts.
Uses Haiku by default to stay cheap — only uses Sonnet when explicitly unthrottled.

Runs on-demand (low frequency) or when The Architect requests lateral thinking.
"""

import json
import logging
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

MAVERICK_PROMPT = """You are Maverick 🎲, the creative lateral thinker at TradingAICenter.
Your job is to find 2nd and 3rd order effects that mainstream analysis ignores.
Think in chains: Event A → Effect B → Impact on Asset C → Trading opportunity in D.

Given the current market context, find 2-3 non-obvious connections.

Return ONLY valid JSON (no markdown):
{
  "connections": [
    {
      "chain": "<Event → Effect → Asset Impact → Opportunity>",
      "ticker": "<most actionable ticker from this chain>",
      "direction": "long" | "short",
      "timeframe": "<days|weeks|months>",
      "conviction": <0.0-1.0>,
      "why_missed": "<why most analysts aren't seeing this>"
    }
  ],
  "wildcard": "<one completely out-of-left-field idea — might be wrong but worth watching>",
  "timestamp": "<ISO timestamp>"
}
Rules:
- Max 3 connections
- conviction must be honest — these are speculative, usually 0.3-0.6
- why_missed is the most important field
"""


class MaverickAgent(BaseAgent):
    agent_id = "maverick"
    agent_name = "Maverick"
    department = "special"
    emoji = "🎲"

    def __init__(self) -> None:
        super().__init__()
        self._throttled: bool = False
        self._context_signals: list[str] = []  # Recent bus signal summaries

    async def run_cycle(self) -> None:
        if self._throttled:
            log.info("[Maverick] Throttled — skipping cycle to save budget")
            return

        if not self._context_signals:
            log.debug("[Maverick] No context yet — waiting")
            return

        await self._generate_lateral_connections()

    async def handle_message(self, msg: BusMessage) -> None:
        # Collect context from high-level bus signals
        if msg.category in {
            MessageCategory.NEWS, MessageCategory.MACRO,
            MessageCategory.ANALYSIS, MessageCategory.SENTIMENT,
        } and msg.type not in {MessageType.AGENT_STATUS}:
            summary = f"[{msg.from_agent}] {str(msg.payload)[:120]}"
            self._context_signals.append(summary)
            if len(self._context_signals) > 20:
                self._context_signals = self._context_signals[-20:]

        # Throttle from Tokin
        elif (msg.payload.get("type") == "throttle"
              and msg.payload.get("target") == "maverick"):
            self._throttled = True
            log.info("[Maverick] Throttled by Tokin — will resume when budget improves")

        # On-demand request from Architect
        elif (msg.type == MessageType.REQUEST_INFO
              and msg.payload.get("request") == "lateral_thinking"):
            await self._generate_lateral_connections()

    async def _generate_lateral_connections(self) -> None:
        await self.set_status(AgentStatus.THINKING, "Finding lateral connections")

        context = "\n".join(self._context_signals[-10:])

        try:
            raw = await self.ask_claude(
                system=MAVERICK_PROMPT,
                user=f"Current market signals:\n{context}\n\nFind non-obvious connections.",
                model=settings.analysis_model,  # Haiku — throttled first, stays cheap
                max_tokens=500,
                temperature=0.8,  # Higher temp for more creative output
            )
            result = json.loads(raw)
        except RuntimeError:
            log.info("[Maverick] LLM vetoed — sitting this one out")
            await self.set_status(AgentStatus.IDLE)
            return
        except Exception as exc:
            log.warning("[Maverick] Lateral thinking failed: %s", exc)
            await self.set_status(AgentStatus.IDLE)
            return

        connections = result.get("connections", [])
        if connections:
            await self.set_status(AgentStatus.SENDING, "Publishing lateral connections")
            await self.publish(
                payload={
                    **result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                category=MessageCategory.ANALYSIS,
                tickers=[c.get("ticker", "") for c in connections if c.get("ticker")],
                confidence=max((c.get("conviction", 0) for c in connections), default=0.3),
                priority=5,
            )
            log.info("[Maverick] 🎲 Published %d lateral connection(s)", len(connections))

        await self.set_status(AgentStatus.IDLE)
