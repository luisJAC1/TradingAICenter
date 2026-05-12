"""
Mood Ring — Sentiment Fusion (Dept 2: Análisis)

Reads all Dept 1 outputs on the Knowledge Bus and fuses them into a single
−100 → +100 sentiment score. Divergences between sources are top-priority signals.

Score bands:
  +70 to +100 → EXTREME GREED
  +30 to  +69 → GREED
  -30 to  +29 → NEUTRAL
  -69 to  -31 → FEAR
 -100 to  -70 → EXTREME FEAR
"""

import json
import logging
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

FUSION_SYSTEM_PROMPT = """You are Mood Ring, the sentiment fusion engine at TradingAICenter.
You receive condensed signal snapshots from multiple Dept 1 research agents and must fuse
them into a single coherent sentiment picture.

Return ONLY valid JSON (no markdown) matching this schema exactly:
{
  "score": <integer -100 to +100>,
  "label": <"EXTREME FEAR"|"FEAR"|"NEUTRAL"|"GREED"|"EXTREME GREED">,
  "signals": {<agent_id>: <contribution -50 to +50>},
  "divergences": [<"AgentA bullish but AgentB bearish — watch carefully">],
  "dominant_catalyst": "<one sentence — what is driving sentiment right now>",
  "confidence": <0.0-1.0>,
  "ticker_scores": {<ticker>: <score -100 to +100>}
}

Rules:
- divergences are the most actionable signals — surface them explicitly
- when social sentiment (Ape/X-Ray) diverges from technical (Charts) → flag it
- extreme readings above +80 or below -80 → confidence must drop (extremes reverse)
- ticker_scores: only include tickers mentioned by 2+ sources
"""

SENTIMENT_CATEGORIES = {
    MessageCategory.SENTIMENT,
    MessageCategory.NEWS,
    MessageCategory.TECHNICAL,
    MessageCategory.MACRO,
    MessageCategory.CRYPTO,
    MessageCategory.FOREX,
    MessageCategory.FUNDAMENTAL,
    MessageCategory.ALTERNATIVE_DATA,
}


class MoodRingAgent(BaseAgent):
    agent_id = "mood-ring"
    agent_name = "Mood Ring"
    department = "analysis"
    emoji = "💎"

    def __init__(self) -> None:
        super().__init__()
        self._signals: dict[str, dict] = {}  # agent_id → latest signal summary
        self._last_score: int = 0
        self._last_label: str = "NEUTRAL"

    async def run_cycle(self) -> None:
        if not self._signals:
            log.info("[Mood Ring] No signals yet — waiting for Dept 1 data")
            return

        await self.set_status(AgentStatus.THINKING, "Fusing sentiment signals")

        signal_digest = self._build_digest()
        try:
            raw = await self.ask_claude(
                system=FUSION_SYSTEM_PROMPT,
                user=f"Fuse these Dept 1 signals into a sentiment score:\n\n{signal_digest}",
                model=settings.analysis_model,
                max_tokens=512,
                temperature=0.2,
            )
            result = json.loads(raw)
        except Exception as exc:
            log.warning("[Mood Ring] Fusion failed: %s", exc)
            await self.set_status(AgentStatus.IDLE)
            return

        self._last_score = result.get("score", 0)
        self._last_label = result.get("label", "NEUTRAL")

        await self.set_status(AgentStatus.SENDING, "Publishing sentiment score")
        await self.publish(
            payload={
                **result,
                "sources": list(self._signals.keys()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.ANALYSIS,
            confidence=result.get("confidence", 0.5),
            priority=3,
        )

        divergences = result.get("divergences", [])
        if divergences:
            await self.publish(
                payload={
                    "type": "sentiment_divergence",
                    "score": self._last_score,
                    "divergences": divergences,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                category=MessageCategory.ANALYSIS,
                msg_type=MessageType.ALERT,
                priority=2,
            )

        log.info("[Mood Ring] Score: %d (%s) | Sources: %d | Divergences: %d",
                 self._last_score, self._last_label, len(self._signals), len(divergences))
        await self.set_status(AgentStatus.IDLE)

    async def handle_message(self, msg: BusMessage) -> None:
        if msg.category not in SENTIMENT_CATEGORIES:
            return
        if msg.type == MessageType.AGENT_STATUS:
            return

        # Store a condensed snapshot per source agent
        self._signals[msg.from_agent] = {
            "agent": msg.from_agent,
            "category": msg.category.value,
            "confidence": msg.confidence,
            "tickers": msg.tickers_relevant[:5],
            "markets": msg.markets_affected,
            "summary": self._extract_summary(msg),
            "ts": msg.timestamp,
        }

    def _extract_summary(self, msg: BusMessage) -> dict:
        p = msg.payload
        # Pull the most signal-rich fields without sending raw bulk data
        keys = (
            "sentiment_score", "direction", "score", "label", "regime",
            "bias", "trend", "mood", "fear_greed", "impact_score",
            "bullish_count", "bearish_count", "signal",
        )
        return {k: p[k] for k in keys if k in p}

    def _build_digest(self) -> str:
        lines = []
        for agent_id, sig in self._signals.items():
            lines.append(
                f"- {agent_id} [{sig['category']}] conf={sig['confidence']:.2f} "
                f"tickers={sig['tickers']} summary={sig['summary']}"
            )
        return "\n".join(lines)
