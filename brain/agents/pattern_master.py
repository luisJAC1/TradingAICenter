"""
Pattern Master — Technical Setup Recognition (Dept 2: Análisis)

Reads Charts agent output from the Knowledge Bus and identifies high-quality
trade setups rated 1–5 stars with full entry/stop/target levels.

The Rule (enforced by Charts, verified here):
  Never publish a setup without:
    1. Volume confirmation (volume > 20-day avg on breakout candle)
    2. Trend alignment (setup direction matches the higher-timeframe trend)
    3. Defined R:R ratio >= 1.5 (minimum acceptable risk/reward)
"""

import json
import logging
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

SETUP_SYSTEM_PROMPT = """You are Pattern Master, a technical analyst at TradingAICenter.
You receive OHLCV data and indicator snapshots from the Charts agent and must identify
high-probability trade setups.

Rate each setup 1–5 stars:
  ⭐⭐⭐⭐⭐ = 5 factors aligned (pattern + volume + trend + catalyst + clean risk)
  ⭐⭐⭐⭐   = 4 factors
  ⭐⭐⭐     = 3 factors (minimum publishable)
  ⭐⭐       = 2 factors (monitor only — do NOT publish as trade signal)
  ⭐        = noise — discard

Return ONLY valid JSON (no markdown):
{
  "setups": [
    {
      "ticker": "<symbol>",
      "stars": <1-5>,
      "pattern": "<e.g. Bull flag on 4h, Double bottom daily>",
      "direction": "long" | "short",
      "entry": <price>,
      "stop": <price>,
      "tp1": <price>,
      "tp2": <price>,
      "tp3": <price | null>,
      "rr_ratio": <float>,
      "volume_confirmed": <bool>,
      "trend_aligned": <bool>,
      "catalyst_present": <bool>,
      "timeframe": "<e.g. 15m, 1h, 4h, daily>",
      "invalidation": "<what price action cancels this setup>"
    }
  ],
  "market_condition": "trending" | "ranging" | "volatile" | "choppy",
  "best_setup": "<ticker of highest-rated setup or null>",
  "notes": "<optional market structure observation>"
}

Rules:
- Only include setups with stars >= 3
- R:R must be >= 1.5 or reject the setup
- volume_confirmed, trend_aligned must both be true for 4+ stars
- tp3 can be null for shorter-term setups
"""


class PatternMasterAgent(BaseAgent):
    agent_id = "pattern-master"
    agent_name = "Pattern Master"
    department = "analysis"
    emoji = "⭐"

    def __init__(self) -> None:
        super().__init__()
        self._charts_data: list[dict] = []  # rolling window of Charts outputs
        self._max_window = 10  # keep last 10 Charts cycles

    async def run_cycle(self) -> None:
        if not self._charts_data:
            log.info("[Pattern Master] No Charts data yet — waiting")
            return

        await self.set_status(AgentStatus.THINKING, "Scanning for setups")

        # Use the most recent Charts snapshot
        latest = self._charts_data[-1]
        ticker_summaries = self._build_ticker_digest(latest)

        if not ticker_summaries:
            await self.set_status(AgentStatus.IDLE)
            return

        try:
            raw = await self.ask_claude(
                system=SETUP_SYSTEM_PROMPT,
                user=f"Identify trade setups from this Charts snapshot:\n\n{ticker_summaries}",
                model=settings.analysis_model,
                max_tokens=800,
                temperature=0.2,
            )
            result = json.loads(raw)
        except Exception as exc:
            log.warning("[Pattern Master] Setup scan failed: %s", exc)
            await self.set_status(AgentStatus.IDLE)
            return

        publishable = [s for s in result.get("setups", []) if s.get("stars", 0) >= 3]

        if publishable:
            tickers = [s["ticker"] for s in publishable]
            await self.set_status(AgentStatus.SENDING, f"Publishing {len(publishable)} setup(s)")
            await self.publish(
                payload={
                    **result,
                    "setups": publishable,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                category=MessageCategory.ANALYSIS,
                tickers=tickers,
                confidence=self._avg_confidence(publishable),
                priority=3,
            )
            log.info("[Pattern Master] Published %d setup(s) | Best: %s",
                     len(publishable), result.get("best_setup"))
        else:
            log.info("[Pattern Master] No setups meeting the 3-star minimum")

        await self.set_status(AgentStatus.IDLE)

    async def handle_message(self, msg: BusMessage) -> None:
        if msg.category == MessageCategory.TECHNICAL and msg.from_agent == "charts":
            self._charts_data.append(msg.payload)
            if len(self._charts_data) > self._max_window:
                self._charts_data.pop(0)

        elif msg.type == MessageType.REQUEST_INFO and msg.payload.get("request") == "setups":
            await self.run_cycle()

    def _build_ticker_digest(self, charts_payload: dict) -> str:
        tickers = charts_payload.get("tickers", {})
        if not tickers:
            return ""
        lines = []
        for symbol, data in tickers.items():
            price = data.get("price", "?")
            change = data.get("change_pct", "?")
            trend = data.get("trend", "?")
            rsi = data.get("rsi", "?")
            volume_ratio = data.get("volume_ratio", "?")
            patterns = data.get("patterns", [])
            lines.append(
                f"{symbol}: price={price} chg={change}% trend={trend} "
                f"rsi={rsi} vol_ratio={volume_ratio} patterns={patterns}"
            )
        return "\n".join(lines)

    def _avg_confidence(self, setups: list[dict]) -> float:
        if not setups:
            return 0.0
        return sum(s.get("stars", 3) / 5 for s in setups) / len(setups)
