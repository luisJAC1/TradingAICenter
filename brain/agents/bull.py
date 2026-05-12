"""
Bull — Bullish Case Builder (Dept 2: Análisis)

On-demand agent. Triggered when The Architect or the system requests a debate.
Reads all available Dept 1 intelligence from the bus window and constructs the
strongest possible bullish case for a given ticker.

Publishes MessageType.DEBATE_ROUND so The Architect can aggregate Bull vs Bear.
"""

import json
import logging
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

BULL_SYSTEM_PROMPT = """You are Bull 🐂, the bullish advocate at TradingAICenter.
Your job is to construct the STRONGEST possible bullish case for a given ticker.
You are NOT balanced — you are a passionate, evidence-based bull.
Find every reason the stock/asset could go up. Ignore nothing positive.

Return ONLY valid JSON (no markdown):
{
  "ticker": "<symbol>",
  "verdict": "BUY" | "STRONG BUY",
  "conviction": <0.0-1.0>,
  "thesis": "<2-3 sentence core bull case>",
  "top_reasons": [
    "<reason 1 — most important>",
    "<reason 2>",
    "<reason 3>"
  ],
  "price_target": <float | null>,
  "timeframe": "<days|weeks|months>",
  "key_catalyst": "<the single event or condition that unlocks the move>",
  "biggest_risk": "<the one thing that kills this bull case>",
  "sentiment_support": "<what sentiment data says>",
  "technical_support": "<what the chart says>",
  "fundamental_support": "<what fundamentals say — or N/A>"
}
"""


class BullAgent(BaseAgent):
    agent_id = "bull"
    agent_name = "Bull"
    department = "analysis"
    emoji = "🐂"

    def __init__(self) -> None:
        super().__init__()
        self._intel: dict[str, list[dict]] = {}  # ticker → [signal dicts]
        self._global_intel: list[dict] = []  # non-ticker-specific signals

    async def run_cycle(self) -> None:
        # Bull is on-demand — no scheduled work
        log.debug("[Bull] Waiting for debate request")

    async def debate(self, ticker: str, context: str = "") -> dict | None:
        """Build the bullish case. Called by handle_message or The Architect."""
        await self.set_status(AgentStatus.THINKING, f"Building bull case for {ticker}")

        intel_digest = self._build_intel_digest(ticker, context)

        try:
            raw = await self.ask_claude(
                system=BULL_SYSTEM_PROMPT,
                user=f"Build the strongest bull case for {ticker}.\n\nAvailable intel:\n{intel_digest}",
                model=settings.reasoning_model,
                max_tokens=600,
                temperature=0.5,
            )
            result = json.loads(raw)
        except Exception as exc:
            log.warning("[Bull] Case building failed for %s: %s", ticker, exc)
            await self.set_status(AgentStatus.IDLE)
            return None

        await self.set_status(AgentStatus.SENDING, f"Publishing bull case for {ticker}")
        await self.publish(
            payload={
                **result,
                "agent": "bull",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.ANALYSIS,
            msg_type=MessageType.DEBATE_ROUND,
            tickers=[ticker],
            confidence=result.get("conviction", 0.5),
            priority=2,
        )

        log.info("[Bull] Published bull case for %s | Conviction: %.0f%%",
                 ticker, result.get("conviction", 0) * 100)
        await self.set_status(AgentStatus.IDLE)
        return result

    async def handle_message(self, msg: BusMessage) -> None:
        # Accumulate Dept 1 intelligence
        if msg.category in {
            MessageCategory.SENTIMENT, MessageCategory.NEWS, MessageCategory.TECHNICAL,
            MessageCategory.FUNDAMENTAL, MessageCategory.MACRO, MessageCategory.CRYPTO,
            MessageCategory.FOREX, MessageCategory.ALTERNATIVE_DATA,
        } and msg.type != MessageType.AGENT_STATUS:
            signal = {
                "from": msg.from_agent,
                "category": msg.category.value,
                "confidence": msg.confidence,
                "payload": self._slim_payload(msg.payload),
            }
            for ticker in (msg.tickers_relevant or []):
                self._intel.setdefault(ticker, []).append(signal)
                if len(self._intel[ticker]) > 20:
                    self._intel[ticker] = self._intel[ticker][-20:]
            if not msg.tickers_relevant:
                self._global_intel.append(signal)
                if len(self._global_intel) > 30:
                    self._global_intel = self._global_intel[-30:]

        # Respond to direct debate request
        elif (
            msg.type == MessageType.REQUEST_INFO
            and msg.payload.get("request") == "bull_case"
        ):
            ticker = msg.payload.get("ticker", "")
            context = msg.payload.get("context", "")
            if ticker:
                await self.debate(ticker, context)

        elif (
            msg.type == MessageType.DEBATE_ROUND
            and msg.payload.get("request_bull_case")
        ):
            ticker = msg.payload.get("ticker", "")
            if ticker:
                await self.debate(ticker)

    def _build_intel_digest(self, ticker: str, context: str) -> str:
        lines = []
        ticker_signals = self._intel.get(ticker, [])
        all_signals = ticker_signals + self._global_intel[-10:]
        for sig in all_signals[-15:]:  # cap at 15 most recent
            lines.append(f"[{sig['from']}|{sig['category']}] {sig['payload']}")
        if context:
            lines.append(f"\nAdditional context: {context}")
        return "\n".join(lines) or "No specific intel available — use general market knowledge."

    def _slim_payload(self, payload: dict) -> dict:
        """Keep only signal-rich keys to limit token waste."""
        keep = {
            "direction", "score", "trend", "signal", "sentiment_score",
            "impact_score", "bullish_count", "bearish_count", "bias",
            "pattern", "setup", "thesis", "summary", "regime", "label",
        }
        return {k: v for k, v in payload.items() if k in keep}
