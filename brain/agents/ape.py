"""
Ape — Reddit & Community Sentiment (Dept 1: Investigación)

Monitors Reddit (WSB, r/stocks, r/cryptocurrency, r/options) for retail
sentiment. Retail sentiment is a CONTRARIAN indicator at extremes.

Data sources (no API key required):
- Reddit public JSON API (reddit.com/r/subreddit.json)
- StockTwits public API
"""

import logging
import re
from collections import Counter
from datetime import datetime, timezone

import httpx

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType

log = logging.getLogger(__name__)

SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "options",
    "investing",
    "cryptocurrency",
]

# Common tickers to scan for (prevents false positives on common words)
KNOWN_TICKERS = {
    "AAPL","NVDA","MSFT","TSLA","AMZN","META","GOOGL","AMD","PLTR","GME",
    "AMC","SPY","QQQ","SOFI","COIN","MSTR","MARA","RIOT","HOOD","RBLX",
    "BTC","ETH","SOL","DOGE","XRP","ADA","AVAX","MATIC","LINK","DOT",
}

HEADERS = {"User-Agent": "TradingAICenter/1.0 (research bot; contact: ljalfaro555@gmail.com)"}


class ApeAgent(BaseAgent):
    agent_id = "ape"
    agent_name = "Ape"
    department = "research"
    emoji = "🦍"

    async def run_cycle(self) -> None:
        await self.set_status(AgentStatus.WORKING, "Scanning Reddit sentiment")

        posts = await self._fetch_reddit_posts()
        sentiment = self._analyze_sentiment(posts)
        trending = self._find_trending_tickers(posts)
        signals = self._generate_signals(sentiment, trending)

        if not posts:
            log.warning("[Ape] No Reddit data retrieved")
            await self.set_status(AgentStatus.IDLE)
            return

        await self.set_status(AgentStatus.SENDING, "Publishing retail sentiment")
        await self.publish(
            payload={
                "posts_sampled": len(posts),
                "subreddits": SUBREDDITS,
                "sentiment": sentiment,
                "trending_tickers": trending[:10],
                "signals": signals,
                "contrarian_note": self._contrarian_note(sentiment, trending),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.SENTIMENT,
            markets=["stocks", "crypto"],
            tickers=[t["ticker"] for t in trending[:5]],
            confidence=0.60,
            priority=5,
        )
        log.info("[Ape] Sampled %d posts | Sentiment: %s | Top ticker: %s",
                 len(posts),
                 sentiment.get("overall", "?"),
                 trending[0]["ticker"] if trending else "none")

        await self.set_status(AgentStatus.IDLE)

    # ── Data fetching ──────────────────────────────────────────────────────────

    async def _fetch_reddit_posts(self) -> list[dict]:
        posts = []
        async with httpx.AsyncClient(timeout=10.0, headers=HEADERS) as client:
            for sub in SUBREDDITS:
                try:
                    r = await client.get(
                        f"https://www.reddit.com/r/{sub}/hot.json",
                        params={"limit": 25},
                    )
                    r.raise_for_status()
                    for item in r.json()["data"]["children"]:
                        d = item["data"]
                        posts.append({
                            "subreddit": sub,
                            "title": d.get("title", ""),
                            "text": d.get("selftext", "")[:500],
                            "score": d.get("score", 0),
                            "upvote_ratio": d.get("upvote_ratio", 0.5),
                            "num_comments": d.get("num_comments", 0),
                            "url": d.get("url", ""),
                        })
                except Exception as exc:
                    log.debug("[Ape] Failed to fetch r/%s: %s", sub, exc)
        return posts

    # ── Analysis ───────────────────────────────────────────────────────────────

    def _analyze_sentiment(self, posts: list[dict]) -> dict:
        if not posts:
            return {"overall": "neutral", "bullish_pct": 50, "bearish_pct": 50}

        bullish_words = {"moon","mooning","rocket","calls","buy","bull","long","squeeze","yolo","chad","tendies","apes"}
        bearish_words = {"puts","short","crash","dump","bear","sell","rekt","baghold","overvalued","bubble","bankrupt","dead"}

        bull_count = 0
        bear_count = 0

        for post in posts:
            text = (post["title"] + " " + post["text"]).lower()
            words = set(re.findall(r"\b\w+\b", text))
            b = len(words & bullish_words)
            br = len(words & bearish_words)
            weight = max(1, post["score"] // 100)
            bull_count += b * weight
            bear_count += br * weight

        total = bull_count + bear_count
        if total == 0:
            return {"overall": "neutral", "bullish_pct": 50, "bearish_pct": 50}

        bull_pct = round(bull_count / total * 100)
        bear_pct = 100 - bull_pct

        if bull_pct >= 65:
            overall = "bullish"
        elif bear_pct >= 65:
            overall = "bearish"
        else:
            overall = "neutral"

        return {
            "overall": overall,
            "bullish_pct": bull_pct,
            "bearish_pct": bear_pct,
            "posts_analyzed": len(posts),
        }

    def _find_trending_tickers(self, posts: list[dict]) -> list[dict]:
        counter: Counter = Counter()
        for post in posts:
            text = (post["title"] + " " + post["text"]).upper()
            words = re.findall(r"\b([A-Z]{2,5})\b", text)
            for word in words:
                if word in KNOWN_TICKERS:
                    counter[word] += max(1, post["score"] // 50)

        return [{"ticker": ticker, "mentions": count} for ticker, count in counter.most_common(20)]

    def _generate_signals(self, sentiment: dict, trending: list[dict]) -> list[dict]:
        signals = []
        bull_pct = sentiment.get("bullish_pct", 50)

        if bull_pct >= 80:
            signals.append({
                "type": "contrarian",
                "signal": "EXTREME_RETAIL_BULLISH",
                "detail": f"Retail {bull_pct}% bullish — historically a SELL signal at extremes",
                "strength": "strong",
                "contrarian": True,
            })
        elif bull_pct <= 20:
            signals.append({
                "type": "contrarian",
                "signal": "EXTREME_RETAIL_BEARISH",
                "detail": f"Retail {bull_pct}% bullish — historically a BUY signal at extremes",
                "strength": "strong",
                "contrarian": True,
            })

        # Meme stock watch
        meme_tickers = {"GME", "AMC", "PLTR", "MSTR", "HOOD"}
        for t in trending[:5]:
            if t["ticker"] in meme_tickers and t["mentions"] > 10:
                signals.append({
                    "type": "meme_watch",
                    "signal": "MEME_ACTIVITY",
                    "ticker": t["ticker"],
                    "detail": f"{t['ticker']} getting heavy Reddit attention ({t['mentions']} weighted mentions)",
                    "strength": "moderate",
                })

        return signals

    def _contrarian_note(self, sentiment: dict, trending: list[dict]) -> str:
        bull_pct = sentiment.get("bullish_pct", 50)
        top = trending[0]["ticker"] if trending else "the market"
        if bull_pct >= 75:
            return f"⚠️ Retail extremely bullish on {top} ({bull_pct}%). Smart money often fades extreme retail consensus."
        if bull_pct <= 25:
            return f"⚠️ Retail extremely bearish ({bull_pct}% bullish). Often marks capitulation bottoms — watch for reversal."
        return f"Retail sentiment mixed ({bull_pct}% bullish) — no strong contrarian signal."

    async def handle_message(self, msg: BusMessage) -> None:
        if msg.type == MessageType.REQUEST_INFO and msg.payload.get("request") == "sentiment_update":
            await self.run_cycle()
