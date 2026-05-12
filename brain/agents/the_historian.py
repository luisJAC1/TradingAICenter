"""
The Historian — Trade Recorder & Backtester (Dept 6: Aprendizaje)

Records every closed trade to SQLite and computes performance metrics.
The Professor reads from this data to improve the system.

Tracks per trade:
  ticker, direction, entry, exit, pnl_pct, result (WIN/LOSS/BE),
  which agents contributed signals, conviction at entry,
  risk_profile active, close_type (stop_hit/tp_hit/forced/user)

Also computes rolling stats:
  win rate, avg win %, avg loss %, Sharpe estimate, best/worst trade

Zero LLM calls — pure data recording.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType

log = logging.getLogger(__name__)

DB_PATH = Path("/app/data/historian.db")  # Mounted volume in Docker


class TheHistorianAgent(BaseAgent):
    agent_id = "the-historian"
    agent_name = "The Historian"
    department = "learning"
    emoji = "📚"

    def __init__(self) -> None:
        super().__init__()
        self._db: sqlite3.Connection | None = None
        self._pending_executions: dict[str, dict] = {}  # ticker → execution data

    async def start(self) -> None:
        await super().start()
        self._init_db()

    async def run_cycle(self) -> None:
        stats = self._compute_stats()
        if not stats:
            log.debug("[The Historian] No trades recorded yet")
            return

        await self.set_status(AgentStatus.WORKING, "Computing performance stats")
        await self.publish(
            payload={
                "type": "performance_summary",
                **stats,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.ANALYSIS,
            priority=6,
        )
        log.info("[The Historian] 📊 Trades: %d | Win rate: %.0f%% | Avg P&L: %.2f%%",
                 stats["total_trades"], stats["win_rate_pct"], stats["avg_pnl_pct"])
        await self.set_status(AgentStatus.IDLE)

    async def handle_message(self, msg: BusMessage) -> None:
        # Trade executed → save entry details for later matching
        if (msg.category == MessageCategory.TRADE_SIGNAL
                and msg.payload.get("type") == "trade_executed"):
            ticker = msg.payload.get("ticker", "")
            self._pending_executions[ticker] = msg.payload

        # Trade closed → record full entry + exit in DB
        elif (msg.category == MessageCategory.RISK
              and msg.payload.get("trade_closed")):
            await self._record_closed_trade(msg.payload)

    # ── Database ──────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        try:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    direction TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    qty INTEGER,
                    pnl_pct REAL,
                    result TEXT,
                    close_type TEXT,
                    risk_profile TEXT,
                    conviction REAL,
                    stars INTEGER,
                    mood_score INTEGER,
                    regime TEXT,
                    executed_at TEXT,
                    closed_at TEXT,
                    plan_json TEXT
                )
            """)
            self._db.commit()
            log.info("[The Historian] DB ready at %s", DB_PATH)
        except Exception as exc:
            log.error("[The Historian] DB init failed: %s", exc)
            self._db = None

    async def _record_closed_trade(self, close_data: dict) -> None:
        if not self._db:
            return

        ticker = close_data.get("ticker", "")
        execution = self._pending_executions.pop(ticker, {})
        plan = close_data.get("plan", execution.get("plan", {}))

        try:
            self._db.execute("""
                INSERT INTO trades (
                    ticker, direction, entry_price, exit_price, qty,
                    pnl_pct, result, close_type, risk_profile, conviction,
                    stars, mood_score, regime, executed_at, closed_at, plan_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                plan.get("direction"),
                plan.get("entry"),
                close_data.get("exit_price"),
                execution.get("qty", 1),
                close_data.get("pnl_pct"),
                close_data.get("result"),
                close_data.get("close_type"),
                plan.get("risk_profile", "BALANCED"),
                plan.get("conviction"),
                plan.get("stars"),
                plan.get("mood_score"),
                plan.get("regime"),
                execution.get("executed_at"),
                datetime.now(timezone.utc).isoformat(),
                json.dumps(plan),
            ))
            self._db.commit()
            icon = "✅" if (close_data.get("pnl_pct") or 0) > 0 else "❌"
            log.info("[The Historian] %s Recorded: %s | P&L: %.2f%%",
                     icon, ticker, close_data.get("pnl_pct", 0))
        except Exception as exc:
            log.error("[The Historian] Failed to record trade %s: %s", ticker, exc)

    def _compute_stats(self) -> dict | None:
        if not self._db:
            return None
        try:
            cur = self._db.execute(
                "SELECT pnl_pct, result, close_type FROM trades ORDER BY id DESC LIMIT 100"
            )
            rows = cur.fetchall()
            if not rows:
                return None

            total = len(rows)
            wins = [r[0] for r in rows if r[1] == "WIN"]
            losses = [r[0] for r in rows if r[1] == "LOSS"]

            return {
                "total_trades": total,
                "wins": len(wins),
                "losses": len(losses),
                "win_rate_pct": round(len(wins) / total * 100, 1) if total else 0,
                "avg_win_pct": round(sum(wins) / len(wins), 2) if wins else 0,
                "avg_loss_pct": round(sum(losses) / len(losses), 2) if losses else 0,
                "avg_pnl_pct": round(sum(r[0] for r in rows if r[0]) / total, 2),
                "best_trade_pct": round(max((r[0] for r in rows if r[0]), default=0), 2),
                "worst_trade_pct": round(min((r[0] for r in rows if r[0]), default=0), 2),
                "stop_hit_count": sum(1 for r in rows if r[2] == "stop_hit"),
                "tp_hit_count": sum(1 for r in rows if r[2] == "tp_hit"),
            }
        except Exception as exc:
            log.error("[The Historian] Stats computation failed: %s", exc)
            return None
