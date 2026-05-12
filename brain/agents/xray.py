"""
X-Ray — Twitter/X & Political Intelligence Scout (Dept 1: Investigación)

Monitors Google News RSS for trending market news and political signals.
Connects social/political buzz to market impact.

In production: add Twitter/X API v2, GDELT, StockGeist.
For now: Google News RSS (free, no API key needed).
"""

import logging
import asyncio
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory

log = logging.getLogger(__name__)

# Political accounts / topics to track via news search
POLITICAL_TOPICS = [
    "Trump market", "Federal Reserve interest rate", "SEC crypto",
    "China tariffs", "OPEC oil", "Elon Musk stocks",
]

MARKET_TOPICS = [
    "stock market today", "S&P 500", "NASDAQ", "Bitcoin price",
    "earnings report", "IPO", "Fed meeting",
]

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


class XRayAgent(BaseAgent):
    agent_id = "x-ray"
    agent_name = "X-Ray"
    department = "research"
    emoji = "🛰️"

    def __init__(self) -> None:
        super().__init__()
        self._http: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._http = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
        await super().start()

    async def stop(self) -> None:
        if self._http:
            await self._http.aclose()
        await super().stop()

    # ── Main cycle ─────────────────────────────────────────────────────────────

    async def run_cycle(self) -> None:
        await self.set_status(AgentStatus.WORKING, "Scanning news and political signals")

        all_items = []
        topics = POLITICAL_TOPICS + MARKET_TOPICS

        # Fetch in parallel (max 5 concurrent to be polite)
        sem = asyncio.Semaphore(5)
        async def fetch(topic: str) -> list[dict]:
            async with sem:
                return await self._fetch_news(topic)

        results = await asyncio.gather(*[fetch(t) for t in topics], return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                all_items.extend(r)

        # Deduplicate by title
        seen = set()
        unique = []
        for item in all_items:
            key = item["title"].lower()[:60]
            if key not in seen:
                seen.add(key)
                unique.append(item)

        if unique:
            await self.set_status(AgentStatus.THINKING, "Analyzing political & market signals")
            scored = self._score_items(unique)

            await self.set_status(AgentStatus.SENDING, "Publishing intelligence report")
            await self.publish(
                payload={
                    "items": scored[:30],  # top 30 most relevant
                    "total_found": len(unique),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                category=MessageCategory.NEWS,
                confidence=0.6,
                priority=4,
            )
            log.info("[X-Ray] Published %d news items", len(scored[:30]))

        await self.set_status(AgentStatus.IDLE)

    # ── News fetching ──────────────────────────────────────────────────────────

    async def _fetch_news(self, topic: str) -> list[dict]:
        if not self._http:
            return []
        url = GOOGLE_NEWS_RSS.format(query=quote(topic))
        try:
            resp = await self._http.get(url)
            resp.raise_for_status()
            return self._parse_rss(resp.text, topic)
        except Exception as exc:
            log.debug("[X-Ray] Fetch error for '%s': %s", topic, exc)
            return []

    def _parse_rss(self, xml: str, topic: str) -> list[dict]:
        """Minimal RSS parser — no external dependency."""
        items = []
        # Split on <item> tags
        parts = xml.split("<item>")[1:]
        for part in parts:
            title = self._extract_tag(part, "title")
            link  = self._extract_tag(part, "link")
            pub   = self._extract_tag(part, "pubDate")
            source = self._extract_tag(part, "source")
            if title:
                items.append({
                    "title": self._clean(title),
                    "link": link,
                    "published": pub,
                    "source": self._clean(source) if source else "Unknown",
                    "topic": topic,
                })
        return items

    def _extract_tag(self, text: str, tag: str) -> str:
        start = text.find(f"<{tag}")
        if start == -1:
            return ""
        start = text.find(">", start) + 1
        end = text.find(f"</{tag}>", start)
        return text[start:end].strip() if end != -1 else ""

    def _clean(self, text: str) -> str:
        import re
        return re.sub(r"<[^>]+>", "", text).strip()

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _score_items(self, items: list[dict]) -> list[dict]:
        """Score items by market relevance keywords."""
        HIGH_IMPACT = [
            "fed", "rate", "inflation", "tariff", "ban", "crash", "surge",
            "record", "bankruptcy", "acquisition", "merger", "ipo", "sec",
            "trump", "powell", "xi", "opec", "nuclear", "sanction",
        ]
        for item in items:
            text = item["title"].lower()
            score = sum(3 for kw in HIGH_IMPACT if kw in text)
            item["relevance_score"] = min(score, 10)

        return sorted(items, key=lambda x: x["relevance_score"], reverse=True)

    # ── Bus handler ───────────────────────────────────────────────────────────

    async def handle_message(self, msg: BusMessage) -> None:
        """Respond to on-demand news requests."""
        if "fetch_news" in msg.payload:
            topic = msg.payload["fetch_news"]
            items = await self._fetch_news(topic)
            if items:
                await self.publish(
                    payload={"items": items, "requested_topic": topic},
                    category=MessageCategory.NEWS,
                    to_agent=msg.from_agent,
                    priority=2,
                )
