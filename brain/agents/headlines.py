"""
Headlines — Financial & Geopolitical News (Dept 1: Investigación)

Finds, analyzes, and assesses trading impact of significant news.
Performs multi-order effect analysis (1st, 2nd, 3rd order effects).

Data sources:
- yfinance news (free, no key)
- Finnhub market news (free, needs FINNHUB_API_KEY env var)
- Google News RSS via feedparser (free, no key)

LLM: Claude analyzes each story for trading impact.
"""

import logging
import hashlib
from datetime import datetime, timezone

import httpx
import yfinance as yf

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"

IMPACT_SYSTEM_PROMPT = """You are Headlines, a financial news analyst at TradingAICenter.
Analyze the provided news headline and assess its trading impact.

For each story return JSON with:
{
  "impact_score": 1-10 (10 = market-moving),
  "direction": "bullish" | "bearish" | "neutral" | "mixed",
  "first_order": "immediate direct effect (1-2 sentences)",
  "second_order": "downstream effects most analysts miss (1 sentence)",
  "third_order": "subtle long-term implications (1 sentence)",
  "affected_tickers": ["list of specific tickers affected"],
  "affected_markets": ["stocks","crypto","forex","commodities"],
  "time_horizon": "immediate" | "days" | "weeks" | "months",
  "confidence": 0.0-1.0,
  "action_note": "what traders should watch or do"
}

Be concise. Only return the JSON object, no markdown.
"""


class HeadlinesAgent(BaseAgent):
    agent_id = "headlines"
    agent_name = "Headlines"
    department = "research"
    emoji = "📰"

    def __init__(self) -> None:
        super().__init__()
        self._seen_hashes: set[str] = set()

    async def run_cycle(self) -> None:
        await self.set_status(AgentStatus.WORKING, "Scanning financial news")

        stories = await self._fetch_news()
        new_stories = self._deduplicate(stories)

        if not new_stories:
            log.info("[Headlines] No new stories to analyze")
            await self.set_status(AgentStatus.IDLE)
            return

        # Analyze top stories with Claude (limit to avoid Tokin hitting budget)
        high_priority = sorted(new_stories, key=lambda s: len(s.get("title", "")), reverse=True)[:5]

        analyzed = []
        await self.set_status(AgentStatus.THINKING, f"Analyzing {len(high_priority)} stories")

        for story in high_priority:
            analysis = await self._analyze_story(story)
            if analysis and analysis.get("impact_score", 0) >= 4:
                analyzed.append({**story, "analysis": analysis})

        if analyzed:
            await self.set_status(AgentStatus.SENDING, "Publishing news intelligence")
            await self.publish(
                payload={
                    "stories": analyzed,
                    "stories_scanned": len(new_stories),
                    "high_impact_count": len(analyzed),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                category=MessageCategory.NEWS,
                markets=list({m for s in analyzed for m in s["analysis"].get("affected_markets", [])}),
                tickers=list({t for s in analyzed for t in s["analysis"].get("affected_tickers", [])}),
                confidence=0.70,
                priority=3,
            )
            log.info("[Headlines] Published %d high-impact stories (of %d scanned)",
                     len(analyzed), len(new_stories))

        await self.set_status(AgentStatus.IDLE)

    # ── Data fetchers ──────────────────────────────────────────────────────────

    async def _fetch_news(self) -> list[dict]:
        stories = []

        # yfinance news for key tickers
        for ticker in ["SPY", "QQQ", "BTC-USD"]:
            try:
                t = yf.Ticker(ticker)
                news = t.news or []
                for item in news[:10]:
                    stories.append({
                        "title": item.get("title", ""),
                        "source": item.get("publisher", "yfinance"),
                        "url": item.get("link", ""),
                        "published": item.get("providerPublishTime", 0),
                        "related_ticker": ticker,
                    })
            except Exception as exc:
                log.debug("[Headlines] yfinance news failed for %s: %s", ticker, exc)

        # Finnhub general market news (if key available)
        finnhub_key = getattr(settings, "finnhub_api_key", "")
        if finnhub_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.get(
                        f"{FINNHUB_BASE}/news",
                        params={"category": "general", "token": finnhub_key},
                    )
                    r.raise_for_status()
                    for item in r.json()[:20]:
                        stories.append({
                            "title": item.get("headline", ""),
                            "source": item.get("source", "Finnhub"),
                            "url": item.get("url", ""),
                            "published": item.get("datetime", 0),
                            "summary": item.get("summary", ""),
                        })
            except Exception as exc:
                log.debug("[Headlines] Finnhub fetch failed: %s", exc)

        return stories

    def _deduplicate(self, stories: list[dict]) -> list[dict]:
        new = []
        for story in stories:
            h = hashlib.md5(story.get("title", "").encode()).hexdigest()
            if h not in self._seen_hashes:
                self._seen_hashes.add(h)
                new.append(story)
        # Keep cache bounded
        if len(self._seen_hashes) > 500:
            self._seen_hashes = set(list(self._seen_hashes)[-300:])
        return new

    async def _analyze_story(self, story: dict) -> dict | None:
        title = story.get("title", "")
        summary = story.get("summary", "")
        if not title:
            return None
        try:
            import json
            text = f"Headline: {title}"
            if summary:
                text += f"\nSummary: {summary[:300]}"
            response = await self.ask_claude(
                system=IMPACT_SYSTEM_PROMPT,
                user=text,
                model=settings.analysis_model,
                max_tokens=400,
                temperature=0.3,
            )
            return json.loads(response)
        except Exception as exc:
            log.debug("[Headlines] Claude analysis failed for '%s': %s", title[:50], exc)
            return None

    async def handle_message(self, msg: BusMessage) -> None:
        if msg.type == MessageType.REQUEST_INFO and msg.payload.get("request") == "news_update":
            await self.run_cycle()
