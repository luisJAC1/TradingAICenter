"""
The Scheduler — Economic Calendar & Global Events (Dept 1: Investigación)

Knows EVERYTHING that is scheduled: economic releases, earnings, central bank
meetings, elections, OPEC, tariff deadlines, OpEx.

Data source: Finnhub Economic Calendar (free: 60 calls/min).
Fallback: manually curated weekly events.
"""

import logging
from datetime import datetime, date, timezone, timedelta
from typing import Any

import httpx

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory
from config import settings

log = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"


class SchedulerAgent(BaseAgent):
    agent_id = "the-scheduler"
    agent_name = "The Scheduler"
    department = "research"
    emoji = "📅"

    def __init__(self) -> None:
        super().__init__()
        self._http: httpx.AsyncClient | None = None
        # Fallback high-impact events (populated when API not available)
        self._known_events: list[dict[str, Any]] = []

    async def start(self) -> None:
        self._http = httpx.AsyncClient(timeout=15.0)
        await super().start()

    async def stop(self) -> None:
        if self._http:
            await self._http.aclose()
        await super().stop()

    # ── Main cycle ─────────────────────────────────────────────────────────────

    async def run_cycle(self) -> None:
        await self.set_status(AgentStatus.WORKING, "Scanning economic calendar")

        today = date.today()
        week_ahead = today + timedelta(days=7)

        events = await self._fetch_economic_calendar(today, week_ahead)

        if not events:
            events = self._get_fallback_events(today)

        high_impact = [e for e in events if e.get("impact") in ("high", "3", 3)]
        upcoming_24h = [
            e for e in events
            if self._is_within_hours(e.get("time", ""), 24)
        ]

        await self.set_status(AgentStatus.THINKING, "Analyzing upcoming events impact")

        summary = self._build_summary(events, high_impact, upcoming_24h)

        await self.set_status(AgentStatus.SENDING, "Publishing calendar intelligence")
        await self.publish(
            payload=summary,
            category=MessageCategory.MACRO,
            confidence=0.9,
            priority=2,
        )
        log.info(
            "[The Scheduler] Published: %d events, %d high-impact, %d in 24h",
            len(events), len(high_impact), len(upcoming_24h),
        )
        await self.set_status(AgentStatus.IDLE)

    # ── Finnhub calendar ───────────────────────────────────────────────────────

    async def _fetch_economic_calendar(
        self, from_date: date, to_date: date
    ) -> list[dict]:
        if not self._http or not settings.anthropic_api_key:
            # No Finnhub key configured — use fallback
            return []

        # Finnhub uses FINNHUB_API_KEY — we'll add it to settings later
        # For now, return empty and fall through to fallback
        return []

    # ── Fallback events ───────────────────────────────────────────────────────

    def _get_fallback_events(self, today: date) -> list[dict[str, Any]]:
        """
        Manually curated recurring high-impact events.
        Used when Finnhub API key is not configured.
        """
        events = []

        # FOMC meetings (roughly every 6 weeks — approximate)
        weekday = today.weekday()
        # Always include the next expected FOMC as an example
        events.append({
            "event": "FOMC Meeting Minutes",
            "impact": "high",
            "country": "US",
            "currency": "USD",
            "time": "Next scheduled",
            "actual": None,
            "forecast": None,
            "previous": None,
            "description": "Federal Reserve monetary policy decision",
            "market_impact": "High volatility across all USD pairs and US equities",
        })
        events.append({
            "event": "CPI (Consumer Price Index)",
            "impact": "high",
            "country": "US",
            "currency": "USD",
            "time": "Mid-month",
            "actual": None,
            "forecast": None,
            "previous": None,
            "description": "US inflation data",
            "market_impact": "Major USD mover; affects Fed rate expectations",
        })
        events.append({
            "event": "Non-Farm Payrolls",
            "impact": "high",
            "country": "US",
            "currency": "USD",
            "time": "First Friday of month",
            "actual": None,
            "forecast": None,
            "previous": None,
            "description": "US employment data",
            "market_impact": "Strongest monthly USD event; 1-2% S&P500 moves common",
        })
        events.append({
            "event": "Crypto Options Expiry (Deribit)",
            "impact": "high",
            "country": "Global",
            "currency": "BTC/ETH",
            "time": "Last Friday of month",
            "actual": None,
            "forecast": None,
            "previous": None,
            "description": "Monthly BTC and ETH options expiry",
            "market_impact": "Increased crypto volatility; pin risk near max pain levels",
        })

        return events

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_within_hours(self, time_str: str, hours: int) -> bool:
        if not time_str or time_str in ("Next scheduled", "Mid-month", "First Friday of month", "Last Friday of month"):
            return False
        try:
            event_time = datetime.fromisoformat(time_str)
            now = datetime.now(timezone.utc)
            delta = event_time - now
            return 0 <= delta.total_seconds() <= hours * 3600
        except Exception:
            return False

    def _build_summary(
        self,
        all_events: list[dict],
        high_impact: list[dict],
        upcoming_24h: list[dict],
    ) -> dict[str, Any]:
        return {
            "date": date.today().isoformat(),
            "total_events_this_week": len(all_events),
            "high_impact_count": len(high_impact),
            "events_next_24h": len(upcoming_24h),
            "all_events": all_events[:20],   # cap for bus message size
            "high_impact_events": high_impact[:10],
            "upcoming_24h": upcoming_24h[:5],
            "trading_recommendation": self._trading_rec(high_impact, upcoming_24h),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _trading_rec(self, high_impact: list, upcoming_24h: list) -> str:
        if upcoming_24h and any(e.get("impact") == "high" for e in upcoming_24h):
            return "REDUCE_SIZE: High-impact event within 24h. Consider 50% position size max."
        if len(high_impact) >= 3:
            return "CAUTION: Multiple high-impact events this week. Stay nimble."
        return "NORMAL: No imminent high-impact events. Standard position sizing applies."

    # ── Bus handler ───────────────────────────────────────────────────────────

    async def handle_message(self, msg: BusMessage) -> None:
        if "get_calendar" in msg.payload:
            await self.run_cycle()
