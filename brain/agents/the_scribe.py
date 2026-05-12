"""
The Scribe — Report Writer (Dept 3: Estrategia)

Converts The Architect's trade plans into polished human-facing reports.
Two output modes:
  1. Trade Signal Report — WhatsApp-formatted alert for each new trade plan
  2. Weekly System Improvement Report — every Sunday 10am ET

The Scribe is the last stop before Dept 4 (The Messenger). It formats
the signal so The Messenger can deliver it to WhatsApp and the dashboard
without any additional transformation.

WhatsApp format (from CLAUDE.md):
  🔔 {TICKER} — {VERDICT} · {conviction}% conviction
  Why: {3 sentences from thesis}
  Entry: ${entry} | Stop: ${stop} | TP1: ${tp1} | TP2: ${tp2}
  Risk: ${risk_amount} ({risk_pct}%) | Target: ${target} (R:R 1:{rr})
  ⚠️ Eleventh Man: {eleventh_man counter-case}
  [✅ APPROVE] [❌ REJECT] [📄 REPORT] [✏️ MODIFY SIZE] [⏸️ WAIT 1H]
"""

import json
import logging
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType
from config import settings

log = logging.getLogger(__name__)

REPORT_SYSTEM_PROMPT = """You are The Scribe ✍️, the report writer at TradingAICenter.
You transform raw trade plans into polished, human-readable WhatsApp messages.

Given a trade plan JSON, write a WhatsApp trading signal in this EXACT format:

🔔 {TICKER} — {VERDICT} · {conviction_pct}% conviction
Why: {3-sentence thesis — clear, confident, no jargon}
Entry: ${entry} | Stop: ${stop} | TP1: ${tp1} | TP2: ${tp2}
Risk: ${risk_dollars} ({risk_pct}%) | R:R 1:{rr_ratio}
⚠️ Eleventh Man: {eleventh_man — 1 sentence, the strongest counter-argument}
[✅ APPROVE] [❌ REJECT] [📄 REPORT] [✏️ MODIFY SIZE] [⏸️ WAIT 1H]

Rules:
- conviction_pct = conviction * 100, rounded to nearest integer
- risk_dollars = portfolio_size * risk_pct / 100 (assume $10,000 portfolio if unknown)
- rr_ratio = format as single decimal e.g. 2.3
- VERDICT must be one of: STRONG BUY / BUY / SHORT / STRONG SHORT
- 3-sentence thesis: first=what, second=why now, third=the edge
- Eleventh Man is always 1 sentence — never skip it
- Return ONLY the formatted message text, no JSON, no markdown wrapper
"""

WEEKLY_REPORT_PROMPT = """You are The Scribe ✍️ writing the weekly System Improvement Report.
Analyze the provided trade history and agent performance data.

Write a concise report with these sections:
1. 📊 Week in Numbers (wins/losses, P&L %, best/worst trade)
2. 🏆 Agent Leaderboard (which agents' signals led to wins)
3. 🔍 What Worked (patterns, conditions, setups that performed)
4. ❌ What Didn't (signals that failed and why)
5. 🔧 System Suggestions (1-3 concrete improvements for next week)

Keep it under 500 words. Trading insight over verbose prose.
Return plain text — no JSON.
"""


class TheScribeAgent(BaseAgent):
    agent_id = "the-scribe"
    agent_name = "The Scribe"
    department = "strategy"
    emoji = "✍️"

    def __init__(self) -> None:
        super().__init__()
        self._pending_plans: list[dict] = []
        self._weekly_history: list[dict] = []  # closed trade summaries

    async def run_cycle(self) -> None:
        """Process any queued trade plans from The Architect."""
        if not self._pending_plans:
            log.debug("[The Scribe] No pending plans to write up")
            return

        plans = self._pending_plans.copy()
        self._pending_plans.clear()

        for plan in plans:
            await self._write_signal_report(plan)

    async def handle_message(self, msg: BusMessage) -> None:
        # New trade plan from The Architect
        if (msg.category == MessageCategory.TRADE_SIGNAL
                and msg.from_agent == "the-architect"
                and msg.type == MessageType.BROADCAST):
            self._pending_plans.append(msg.payload)
            # Write immediately — don't wait for next cycle
            await self._write_signal_report(msg.payload)

        # Closed trade result (from Watchdog/Trigger) — track for weekly report
        elif msg.category == MessageCategory.RISK and msg.payload.get("trade_closed"):
            self._weekly_history.append(msg.payload)
            if len(self._weekly_history) > 100:
                self._weekly_history = self._weekly_history[-100:]

        # Weekly report request (from scheduler or REQUEST_INFO)
        elif (msg.type == MessageType.REQUEST_INFO
              and msg.payload.get("request") == "weekly_report"):
            await self._write_weekly_report()

    # ── Report writers ─────────────────────────────────────────────────────────

    async def _write_signal_report(self, plan: dict) -> None:
        ticker = plan.get("ticker", "???")
        if plan.get("decision") != "TRADE":
            return

        await self.set_status(AgentStatus.THINKING, f"Writing signal report: {ticker}")
        try:
            formatted = await self.ask_claude(
                system=REPORT_SYSTEM_PROMPT,
                user=f"Write the WhatsApp signal for this trade plan:\n\n{json.dumps(plan, indent=2)}",
                model=settings.reasoning_model,
                max_tokens=400,
                temperature=0.4,
            )
        except Exception as exc:
            log.warning("[The Scribe] Signal formatting failed for %s: %s", ticker, exc)
            formatted = self._fallback_format(plan)

        await self.set_status(AgentStatus.SENDING, f"Publishing report: {ticker}")
        await self.publish(
            payload={
                "type": "trade_signal_report",
                "ticker": ticker,
                "whatsapp_message": formatted,
                "raw_plan": plan,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.TRADE_SIGNAL,
            msg_type=MessageType.BROADCAST,
            tickers=[ticker],
            confidence=plan.get("conviction", 0.5),
            priority=1,  # Highest priority — this goes to The Messenger next
        )

        log.info("[The Scribe] Signal report published for %s", ticker)
        await self.set_status(AgentStatus.IDLE)

    async def _write_weekly_report(self) -> None:
        await self.set_status(AgentStatus.THINKING, "Writing weekly system report")

        history_text = json.dumps(self._weekly_history[-50:], indent=2) if self._weekly_history \
            else "No closed trades this week."

        try:
            report = await self.ask_claude(
                system=WEEKLY_REPORT_PROMPT,
                user=f"Weekly trade history:\n{history_text}",
                model=settings.reasoning_model,
                max_tokens=800,
                temperature=0.5,
            )
        except Exception as exc:
            log.warning("[The Scribe] Weekly report failed: %s", exc)
            await self.set_status(AgentStatus.IDLE)
            return

        await self.set_status(AgentStatus.SENDING, "Publishing weekly report")
        await self.publish(
            payload={
                "type": "weekly_report",
                "report": report,
                "period_trades": len(self._weekly_history),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.ANALYSIS,
            msg_type=MessageType.BROADCAST,
            priority=4,
        )
        log.info("[The Scribe] Weekly report published (%d trades reviewed)",
                 len(self._weekly_history))
        await self.set_status(AgentStatus.IDLE)

    def _fallback_format(self, plan: dict) -> str:
        """Plain-text fallback if Claude call fails."""
        ticker = plan.get("ticker", "???")
        verdict = "BUY" if plan.get("direction") == "long" else "SHORT"
        conv = int(plan.get("conviction", 0) * 100)
        entry = plan.get("entry", "TBD")
        stop = plan.get("stop", "TBD")
        tp1 = plan.get("tp1", "TBD")
        tp2 = plan.get("tp2", "TBD")
        rr = plan.get("rr_ratio", "?")
        risk = plan.get("risk_pct", "?")
        em = plan.get("eleventh_man", "No counter-argument provided.")
        thesis = plan.get("thesis", "See full report.")
        return (
            f"🔔 {ticker} — {verdict} · {conv}% conviction\n"
            f"Why: {thesis}\n"
            f"Entry: ${entry} | Stop: ${stop} | TP1: ${tp1} | TP2: ${tp2}\n"
            f"Risk: {risk}% | R:R 1:{rr}\n"
            f"⚠️ Eleventh Man: {em}\n"
            f"[✅ APPROVE] [❌ REJECT] [📄 REPORT] [✏️ MODIFY SIZE] [⏸️ WAIT 1H]"
        )
