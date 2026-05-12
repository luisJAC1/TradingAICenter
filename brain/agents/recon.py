"""
Recon — Alternative Data & Dark Intelligence (Dept 1: Investigación)

Finds hidden signals mainstream analysis misses:
- Unusual options activity (large OTM contracts via yfinance)
- Insider transactions (SEC EDGAR, free)
- Short interest data (yfinance)

Smart money hierarchy: Congressional trading > Dark pool blocks >
Unusual options > Insider buying > Short interest > ETF flows

Data sources (all free, no key required):
- yfinance options chains for unusual activity detection
- SEC EDGAR full-text search for insider filings
"""

import logging
from datetime import datetime, timezone

import httpx
import yfinance as yf

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType

log = logging.getLogger(__name__)

DEFAULT_WATCHLIST = ["AAPL", "NVDA", "MSFT", "TSLA", "AMZN", "META", "SPY", "QQQ", "AMD", "PLTR"]
SEC_EDGAR_BASE = "https://efts.sec.gov/LATEST/search-index"


class ReconAgent(BaseAgent):
    agent_id = "recon"
    agent_name = "Recon"
    department = "research"
    emoji = "🕵️"

    def __init__(self) -> None:
        super().__init__()
        self.watchlist: list[str] = DEFAULT_WATCHLIST.copy()

    async def run_cycle(self) -> None:
        await self.set_status(AgentStatus.WORKING, "Scanning for unusual market activity")

        unusual_options = self._scan_unusual_options()
        insider_activity = await self._fetch_insider_filings()
        short_data = self._fetch_short_interest()

        signals = self._generate_signals(unusual_options, insider_activity, short_data)

        if not signals and not unusual_options:
            await self.set_status(AgentStatus.IDLE)
            return

        await self.set_status(AgentStatus.SENDING, "Publishing alternative data intelligence")
        await self.publish(
            payload={
                "unusual_options": unusual_options[:10],
                "insider_activity": insider_activity[:10],
                "short_interest": short_data,
                "signals": signals,
                "smart_money_note": self._smart_money_summary(signals),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.ALTERNATIVE_DATA,
            markets=["stocks", "options"],
            tickers=list({s.get("ticker") for s in signals if s.get("ticker")}),
            confidence=0.65,
            priority=3,
        )
        log.info("[Recon] Found %d unusual options, %d insider filings, %d signals",
                 len(unusual_options), len(insider_activity), len(signals))

        await self.set_status(AgentStatus.IDLE)

    # ── Options scanning ───────────────────────────────────────────────────────

    def _scan_unusual_options(self) -> list[dict]:
        unusual = []
        for ticker in self.watchlist[:5]:  # Limit API calls
            try:
                t = yf.Ticker(ticker)
                expirations = t.options
                if not expirations:
                    continue

                # Check the nearest 2 expiration dates
                for exp in expirations[:2]:
                    chain = t.option_chain(exp)
                    for opt_type, df in [("CALL", chain.calls), ("PUT", chain.puts)]:
                        if df is None or df.empty:
                            continue

                        # Unusual: volume >> open interest (new money coming in)
                        df = df.copy()
                        df = df[df["volume"].notna() & df["openInterest"].notna()]
                        df = df[df["openInterest"] > 0]
                        df["vol_oi_ratio"] = df["volume"] / df["openInterest"]

                        # Flag contracts where volume is 5x+ open interest
                        flagged = df[df["vol_oi_ratio"] >= 5].sort_values("volume", ascending=False)

                        for _, row in flagged.head(3).iterrows():
                            unusual.append({
                                "ticker": ticker,
                                "type": opt_type,
                                "expiry": exp,
                                "strike": float(row["strike"]),
                                "volume": int(row["volume"]),
                                "open_interest": int(row["openInterest"]),
                                "vol_oi_ratio": round(float(row["vol_oi_ratio"]), 1),
                                "implied_volatility": round(float(row["impliedVolatility"]) * 100, 1) if "impliedVolatility" in row else None,
                                "last_price": float(row["lastPrice"]) if "lastPrice" in row else None,
                            })
            except Exception as exc:
                log.debug("[Recon] Options scan failed for %s: %s", ticker, exc)

        # Sort by vol/OI ratio descending
        return sorted(unusual, key=lambda x: x["vol_oi_ratio"], reverse=True)

    # ── SEC EDGAR insider filings ──────────────────────────────────────────────

    async def _fetch_insider_filings(self) -> list[dict]:
        filings = []
        try:
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "TradingAICenter ljalfaro555@gmail.com"}) as client:
                r = await client.get(
                    "https://efts.sec.gov/LATEST/search-index?q=%22Form+4%22&dateRange=custom&startdt=2026-04-21&enddt=2026-04-28&hits.hits.total.value=true&hits.hits._source.period_of_report=true&hits.hits._source.entity_name=true&hits.hits._source.file_date=true",
                )
                # SEC EDGAR returns complex JSON; parse lightly
                data = r.json()
                hits = data.get("hits", {}).get("hits", [])
                for hit in hits[:10]:
                    src = hit.get("_source", {})
                    filings.append({
                        "entity": src.get("entity_name", "Unknown"),
                        "filing_date": src.get("file_date", ""),
                        "form_type": src.get("form_type", "4"),
                    })
        except Exception as exc:
            log.debug("[Recon] SEC EDGAR fetch failed: %s", exc)

        return filings

    # ── Short interest ─────────────────────────────────────────────────────────

    def _fetch_short_interest(self) -> list[dict]:
        result = []
        for ticker in self.watchlist[:5]:
            try:
                t = yf.Ticker(ticker)
                info = t.info or {}
                short_ratio = info.get("shortRatio")
                short_pct = info.get("shortPercentOfFloat")
                if short_ratio or short_pct:
                    result.append({
                        "ticker": ticker,
                        "short_ratio": round(short_ratio, 1) if short_ratio else None,
                        "short_pct_float": round(short_pct * 100, 1) if short_pct else None,
                    })
            except Exception as exc:
                log.debug("[Recon] Short interest failed for %s: %s", ticker, exc)
        return result

    # ── Signal generation ──────────────────────────────────────────────────────

    def _generate_signals(
        self,
        unusual_options: list[dict],
        insider_activity: list[dict],
        short_data: list[dict],
    ) -> list[dict]:
        signals = []

        # Unusual options signals
        for opt in unusual_options[:3]:
            direction = "bullish" if opt["type"] == "CALL" else "bearish"
            signals.append({
                "type": "unusual_options",
                "signal": f"UNUSUAL_{opt['type']}S",
                "ticker": opt["ticker"],
                "direction": direction,
                "detail": (
                    f"{opt['ticker']} {opt['type']}s at ${opt['strike']} exp {opt['expiry']}: "
                    f"volume {opt['volume']:,} vs OI {opt['open_interest']:,} "
                    f"(ratio: {opt['vol_oi_ratio']}x)"
                ),
                "strength": "strong" if opt["vol_oi_ratio"] >= 10 else "moderate",
            })

        # High short interest (potential squeeze candidates)
        for s in short_data:
            if s.get("short_ratio") and s["short_ratio"] >= 10:
                signals.append({
                    "type": "short_squeeze_candidate",
                    "signal": "HIGH_SHORT_RATIO",
                    "ticker": s["ticker"],
                    "direction": "watch",
                    "detail": f"{s['ticker']} short ratio {s['short_ratio']} days — squeeze potential if catalyst appears",
                    "strength": "moderate",
                })

        return signals

    def _smart_money_summary(self, signals: list[dict]) -> str:
        if not signals:
            return "No unusual smart money activity detected in current scan."
        call_signals = [s for s in signals if "CALLS" in s.get("signal", "")]
        put_signals  = [s for s in signals if "PUTS" in s.get("signal", "")]
        if call_signals and not put_signals:
            tickers = list({s["ticker"] for s in call_signals})
            return f"Smart money accumulating calls on {', '.join(tickers)}. Institutional interest detected."
        if put_signals and not call_signals:
            tickers = list({s["ticker"] for s in put_signals})
            return f"Unusual put activity on {', '.join(tickers)}. Someone may be hedging or betting on a drop."
        return f"Mixed smart money signals: {len(call_signals)} bullish, {len(put_signals)} bearish plays detected."

    async def handle_message(self, msg: BusMessage) -> None:
        if msg.type == MessageType.REQUEST_INFO and "watchlist" in msg.payload:
            tickers = msg.payload["watchlist"]
            if isinstance(tickers, list):
                self.watchlist = tickers
