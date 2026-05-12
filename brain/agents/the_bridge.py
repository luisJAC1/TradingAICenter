"""
The Bridge — Cross-Asset Correlation Tracker (Dept 2: Análisis)

Monitors correlations between asset classes (stocks, crypto, bonds, forex, commodities).
When a historically stable correlation breaks down, that divergence is alpha.

Key relationships tracked:
  SPY  ↔ BTC      (risk-on / risk-off proxy)
  SPY  ↔ TLT      (stocks vs bonds: inverse = normal)
  DXY  ↔ SPY      (dollar strength vs equity)
  DXY  ↔ BTC      (dollar vs crypto: usually inverse)
  GLD  ↔ TLT      (gold vs bonds: safe-haven flows)
  VIX  ↔ SPY      (fear vs equity: should be inverse)
  QQQ  ↔ SPY      (growth vs broad: divergence = sector rotation)
"""

import json
import logging
from datetime import datetime, timezone

import pandas as pd

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings
from market.market_data import fetch_bars

log = logging.getLogger(__name__)

CORRELATION_PAIRS = [
    ("SPY",  "BTC-USD"),
    ("SPY",  "TLT"),
    ("DX-Y.NYB", "SPY"),
    ("DX-Y.NYB", "BTC-USD"),
    ("GLD",  "TLT"),
    ("^VIX", "SPY"),
    ("QQQ",  "SPY"),
]

WINDOWS = [20, 60, 200]

BRIDGE_SYSTEM_PROMPT = """You are The Bridge 🌉, a cross-asset correlation analyst at TradingAICenter.
You receive correlation data between asset pairs and must identify:
1. Which correlations are breaking from their historical norms
2. What regime shift (if any) those breaks signal
3. What trading edge those breaks create

Return ONLY valid JSON (no markdown):
{
  "regime": "risk-on" | "risk-off" | "mixed" | "transitioning",
  "regime_confidence": <0.0-1.0>,
  "breaks": [
    {
      "pair": "<AssetA/AssetB>",
      "current_corr": <float>,
      "historical_norm": <float>,
      "deviation": "<describe how far off normal>",
      "signal": "<what this divergence means for traders>",
      "actionable": <bool>
    }
  ],
  "dominant_theme": "<one sentence: what macro theme explains today's correlations>",
  "watch": "<the one pair to watch most closely right now>",
  "notes": "<optional unusual observation>"
}
"""


class TheBridgeAgent(BaseAgent):
    agent_id = "the-bridge"
    agent_name = "The Bridge"
    department = "analysis"
    emoji = "🌉"

    def __init__(self) -> None:
        super().__init__()
        self._last_corr_data: dict | None = None

    async def run_cycle(self) -> None:
        await self.set_status(AgentStatus.WORKING, "Fetching price data")

        corr_data = await self._compute_correlations()
        if not corr_data:
            await self.set_status(AgentStatus.IDLE)
            return

        self._last_corr_data = corr_data

        await self.set_status(AgentStatus.THINKING, "Analyzing correlation breaks")
        digest = self._build_digest(corr_data)

        try:
            raw = await self.ask_claude(
                system=BRIDGE_SYSTEM_PROMPT,
                user=f"Analyze these cross-asset correlations for breaks and regime signals:\n\n{digest}",
                model=settings.analysis_model,
                max_tokens=600,
                temperature=0.3,
            )
            result = json.loads(raw)
        except Exception as exc:
            log.warning("[The Bridge] Analysis failed: %s", exc)
            await self.set_status(AgentStatus.IDLE)
            return

        breaks = result.get("breaks", [])
        actionable_breaks = [b for b in breaks if b.get("actionable")]

        await self.set_status(AgentStatus.SENDING, "Publishing correlation analysis")
        await self.publish(
            payload={
                **result,
                "raw_correlations": corr_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.ANALYSIS,
            confidence=result.get("regime_confidence", 0.5),
            priority=3,
        )

        if actionable_breaks:
            await self.publish(
                payload={
                    "type": "correlation_break",
                    "regime": result.get("regime"),
                    "breaks": actionable_breaks,
                    "dominant_theme": result.get("dominant_theme"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                category=MessageCategory.ANALYSIS,
                msg_type=MessageType.ALERT,
                priority=2,
            )

        log.info("[The Bridge] Regime: %s | Breaks: %d (actionable: %d)",
                 result.get("regime"), len(breaks), len(actionable_breaks))
        await self.set_status(AgentStatus.IDLE)

    async def handle_message(self, msg: BusMessage) -> None:
        if msg.type == MessageType.REQUEST_INFO and msg.payload.get("request") == "correlations":
            await self.run_cycle()

    async def _compute_correlations(self) -> dict | None:
        """Fetch price histories and compute rolling correlations."""
        all_symbols = list({s for pair in CORRELATION_PAIRS for s in pair})
        try:
            # Download 210 trading days (covers 200d window + buffer)
            df = await _fetch_prices(all_symbols, period="13mo")
            if df is None or df.empty:
                return None
        except Exception as exc:
            log.warning("[The Bridge] Price fetch failed: %s", exc)
            return None

        result: dict[str, dict] = {}
        for sym_a, sym_b in CORRELATION_PAIRS:
            pair_key = f"{sym_a}/{sym_b}"
            if sym_a not in df.columns or sym_b not in df.columns:
                continue

            series_a = df[sym_a].dropna()
            series_b = df[sym_b].dropna()
            common = series_a.index.intersection(series_b.index)
            if len(common) < 30:
                continue

            a = series_a[common]
            b = series_b[common]

            pair_data: dict[str, float | None] = {}
            for w in WINDOWS:
                if len(common) >= w:
                    corr = a.tail(w).corr(b.tail(w))
                    pair_data[f"corr_{w}d"] = round(float(corr), 3) if pd.notna(corr) else None
                else:
                    pair_data[f"corr_{w}d"] = None

            result[pair_key] = pair_data

        return result if result else None

    def _build_digest(self, corr_data: dict) -> str:
        lines = []
        for pair, data in corr_data.items():
            c20 = data.get("corr_20d", "N/A")
            c60 = data.get("corr_60d", "N/A")
            c200 = data.get("corr_200d", "N/A")
            lines.append(f"{pair}: 20d={c20}  60d={c60}  200d={c200}")
        return "\n".join(lines)


async def _fetch_prices(symbols: list[str], period: str) -> pd.DataFrame | None:
    """Download adjusted close prices. Runs synchronously in a thread pool."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch, symbols, period)


def _sync_fetch(symbols: list[str], period: str) -> pd.DataFrame | None:
    try:
        by_sym = fetch_bars(symbols, timeframe="1d", period=period)
        if not by_sym:
            return None
        # Build a wide DataFrame of Close prices indexed by date.
        closes = pd.DataFrame({sym: df["Close"] for sym, df in by_sym.items() if not df.empty})
        if closes.empty:
            return None
        return closes.sort_index().ffill()
    except Exception:
        return None
