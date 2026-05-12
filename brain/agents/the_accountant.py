"""
The Accountant — Fundamental Data Miner (Dept 1: Investigación)

Evaluates intrinsic value via financial statements, ratios (P/E, P/B, ROE, etc.),
insider activity, and analyst ratings. Flags red-flag stocks.

Data sources:
- yfinance (free, no key) — financials, info, recommendations
- LLM: Claude synthesizes the fundamentals into a plain-language verdict.
"""

import logging
from datetime import datetime, timezone

import yfinance as yf

from config import settings
from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType

log = logging.getLogger(__name__)

DEFAULT_WATCHLIST = ["AAPL", "NVDA", "MSFT", "TSLA", "AMZN", "META", "GOOGL", "AMD"]

FUNDAMENTAL_SYSTEM_PROMPT = """You are The Accountant, a fundamental analyst at TradingAICenter.
Analyze the provided financial data for a stock and return a concise assessment.

Return JSON:
{
  "verdict": "UNDERVALUED" | "FAIR_VALUE" | "OVERVALUED" | "AVOID",
  "confidence": 0.0-1.0,
  "key_strengths": ["list of max 3 strengths"],
  "red_flags": ["list of any red flags found"],
  "valuation_score": 1-10 (10 = very attractive valuation),
  "quality_score": 1-10 (10 = very high-quality business),
  "plain_language_summary": "2 sentences a non-quant can understand",
  "watch_for": "what to monitor going forward"
}

RED FLAG TRIGGERS: Revenue declining + stock rising, D/E > 2x, insider selling > $10M,
receivables growing faster than revenue, auditor changes, negative free cash flow 3+ quarters.

Only return the JSON object, no markdown.
"""


class TheAccountantAgent(BaseAgent):
    agent_id = "the-accountant"
    agent_name = "The Accountant"
    department = "research"
    emoji = "🧮"

    def __init__(self) -> None:
        super().__init__()
        self.watchlist: list[str] = DEFAULT_WATCHLIST.copy()

    async def run_cycle(self) -> None:
        await self.set_status(AgentStatus.WORKING, "Mining fundamental data")

        results = []
        for ticker in self.watchlist[:4]:  # Limit per cycle to manage LLM cost
            try:
                data = self._fetch_fundamentals(ticker)
                if data:
                    await self.set_status(AgentStatus.THINKING, f"Analyzing {ticker} fundamentals")
                    analysis = await self._analyze_fundamentals(ticker, data)
                    if analysis:
                        results.append({"ticker": ticker, "data": data, "analysis": analysis})
            except Exception as exc:
                log.warning("[Accountant] Error analyzing %s: %s", ticker, exc)

        if results:
            red_flag_tickers = [r["ticker"] for r in results if r["analysis"].get("red_flags")]
            await self.set_status(AgentStatus.SENDING, "Publishing fundamental analysis")
            await self.publish(
                payload={
                    "fundamentals": results,
                    "tickers_analyzed": [r["ticker"] for r in results],
                    "red_flag_tickers": red_flag_tickers,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                category=MessageCategory.FUNDAMENTAL,
                markets=["stocks"],
                tickers=[r["ticker"] for r in results],
                confidence=0.68,
                priority=5,
            )
            log.info("[Accountant] Analyzed %d tickers | Red flags: %s",
                     len(results), red_flag_tickers or "none")

        await self.set_status(AgentStatus.IDLE)

    # ── Data fetching ──────────────────────────────────────────────────────────

    def _fetch_fundamentals(self, ticker: str) -> dict | None:
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}

            if not info.get("marketCap"):
                return None

            # Key ratios
            pe   = info.get("trailingPE")
            pb   = info.get("priceToBook")
            ps   = info.get("priceToSalesTrailing12Months")
            de   = info.get("debtToEquity")
            roe  = info.get("returnOnEquity")
            roa  = info.get("returnOnAssets")
            margin = info.get("profitMargins")
            rev_growth = info.get("revenueGrowth")
            fcf  = info.get("freeCashflow")
            mktcap = info.get("marketCap")
            insider_pct = info.get("heldPercentInsiders")

            # Analyst recommendations
            rec = info.get("recommendationKey", "none")  # strong_buy, buy, hold, sell, etc.
            target_mean = info.get("targetMeanPrice")
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")

            upside = None
            if target_mean and current_price:
                upside = round((target_mean / current_price - 1) * 100, 1)

            return {
                "ticker": ticker,
                "name": info.get("shortName", ticker),
                "sector": info.get("sector", "Unknown"),
                "market_cap_b": round(mktcap / 1e9, 1) if mktcap else None,
                "current_price": current_price,
                "pe_ratio": round(pe, 1) if pe else None,
                "pb_ratio": round(pb, 2) if pb else None,
                "ps_ratio": round(ps, 2) if ps else None,
                "debt_to_equity": round(de / 100, 2) if de else None,
                "roe_pct": round(roe * 100, 1) if roe else None,
                "roa_pct": round(roa * 100, 1) if roa else None,
                "profit_margin_pct": round(margin * 100, 1) if margin else None,
                "revenue_growth_pct": round(rev_growth * 100, 1) if rev_growth else None,
                "free_cash_flow_b": round(fcf / 1e9, 2) if fcf else None,
                "insider_ownership_pct": round(insider_pct * 100, 1) if insider_pct else None,
                "analyst_recommendation": rec,
                "analyst_target_price": target_mean,
                "analyst_upside_pct": upside,
            }
        except Exception as exc:
            log.debug("[Accountant] Failed to fetch %s: %s", ticker, exc)
            return None

    async def _analyze_fundamentals(self, ticker: str, data: dict) -> dict | None:
        import json
        summary = (
            f"Ticker: {ticker} ({data.get('name')})\n"
            f"Sector: {data.get('sector')}\n"
            f"Market Cap: ${data.get('market_cap_b')}B\n"
            f"P/E: {data.get('pe_ratio')} | P/B: {data.get('pb_ratio')} | P/S: {data.get('ps_ratio')}\n"
            f"D/E: {data.get('debt_to_equity')} | ROE: {data.get('roe_pct')}% | ROA: {data.get('roa_pct')}%\n"
            f"Profit Margin: {data.get('profit_margin_pct')}% | Rev Growth: {data.get('revenue_growth_pct')}%\n"
            f"Free Cash Flow: ${data.get('free_cash_flow_b')}B\n"
            f"Insider Ownership: {data.get('insider_ownership_pct')}%\n"
            f"Analyst Rating: {data.get('analyst_recommendation')} | Target: ${data.get('analyst_target_price')} ({data.get('analyst_upside_pct')}% upside)"
        )
        try:
            response = await self.ask_claude(
                system=FUNDAMENTAL_SYSTEM_PROMPT,
                user=summary,
                model=settings.analysis_model,
                max_tokens=400,
                temperature=0.2,
            )
            return json.loads(response)
        except Exception as exc:
            log.debug("[Accountant] Claude analysis failed for %s: %s", ticker, exc)
            return None

    async def handle_message(self, msg: BusMessage) -> None:
        if msg.type == MessageType.REQUEST_INFO and "watchlist" in msg.payload:
            tickers = msg.payload["watchlist"]
            if isinstance(tickers, list):
                self.watchlist = tickers
        elif msg.type == MessageType.REQUEST_INFO and msg.payload.get("request") == "fundamentals_update":
            await self.run_cycle()
