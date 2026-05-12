"""
TradingAICenter — Python Brain
FastAPI server (port 8791)

Manages all 26 trading agents, the Knowledge Bus, ChromaDB, and
the real-time bridge to the Claw-Empire UI.
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from knowledge_bus.bus import bus
from memory.semantic import memory
from bridge.ui_bridge import bridge
from agents.charts import ChartsAgent
from agents.xray import XRayAgent
from agents.scheduler_agent import SchedulerAgent
from agents.cryptid import CryptidAgent
from agents.globe import GlobeAgent
from agents.ape import ApeAgent
from agents.headlines import HeadlinesAgent
from agents.the_accountant import TheAccountantAgent
from agents.recon import ReconAgent
# Dept 2 — Análisis (Analysis)
from agents.mood_ring import MoodRingAgent
from agents.pattern_master import PatternMasterAgent
from agents.bull import BullAgent
from agents.bear import BearAgent
from agents.the_bridge import TheBridgeAgent
# Dept 3 — Estrategia (Strategy)
from agents.the_architect import TheArchitectAgent
from agents.the_scribe import TheScribeAgent
# Dept 4 — Decisión y Riesgo (Decision & Risk)
from agents.the_shield import TheShieldAgent
from agents.the_boss import TheBossAgent
from agents.the_messenger import TheMessengerAgent
# Dept 5 — Ejecución (Execution)
from agents.the_trigger import TheTriggerAgent
from agents.the_watchdog import TheWatchdogAgent
# Dept 6 — Aprendizaje (Learning)
from agents.the_historian import TheHistorianAgent
from agents.the_professor import TheProfessorAgent
# Special / Meta
from agents.tokin import TokinAgent
from agents.the_eleventh_man import TheEleventhManAgent
from agents.maverick import MaverickAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Agent registry ─────────────────────────────────────────────────────────────
AGENTS = {
    # Dept 1 — Investigación (Research)
    "charts":           ChartsAgent(),
    "x-ray":            XRayAgent(),
    "the-scheduler":    SchedulerAgent(),
    "cryptid":          CryptidAgent(),
    "globe":            GlobeAgent(),
    "ape":              ApeAgent(),
    "headlines":        HeadlinesAgent(),
    "the-accountant":   TheAccountantAgent(),
    "recon":            ReconAgent(),
    # Dept 2 — Análisis (Analysis)
    "mood-ring":        MoodRingAgent(),
    "pattern-master":   PatternMasterAgent(),
    "bull":             BullAgent(),
    "bear":             BearAgent(),
    "the-bridge":       TheBridgeAgent(),
    # Dept 3 — Estrategia (Strategy)
    "the-architect":    TheArchitectAgent(),
    "the-scribe":       TheScribeAgent(),
    # Dept 4 — Decisión y Riesgo (Decision & Risk)
    "the-shield":       TheShieldAgent(),
    "the-boss":         TheBossAgent(),
    "the-messenger":    TheMessengerAgent(),
    # Dept 5 — Ejecución (Execution)
    "the-trigger":      TheTriggerAgent(),
    "the-watchdog":     TheWatchdogAgent(),
    # Dept 6 — Aprendizaje (Learning)
    "the-historian":    TheHistorianAgent(),
    "the-professor":    TheProfessorAgent(),
    # Special / Meta
    "tokin":            TokinAgent(),
    "the-eleventh-man": TheEleventhManAgent(),
    "maverick":         MaverickAgent(),
}

# ── Scheduler ──────────────────────────────────────────────────────────────────
scheduler = AsyncIOScheduler(timezone="UTC")

# ── WebSocket connections from external clients ────────────────────────────────
_ws_clients: list[WebSocket] = []


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("TradingAICenter Brain starting up...")
    log.info("=" * 60)

    # Apply risk profile (overrides risk fields based on RISK_PROFILE env var)
    settings.apply_risk_profile()
    log.info("[Brain] Risk profile: %s | %.1f%%/trade | %.1f%% heat | %d max plans",
             settings.risk_profile, settings.risk_pct_per_trade,
             settings.max_portfolio_heat, settings.max_simultaneous_plans)

    # Connect infrastructure
    await bus.connect()
    await memory.connect()
    await bridge.start()

    # Start Tokin first — must be listening before any LLM calls happen
    await AGENTS["tokin"].start()
    # Start all other agents
    for agent_id, agent in AGENTS.items():
        if agent_id != "tokin":
            await agent.start()

    # Schedule agent cycles
    scheduler.add_job(
        AGENTS["charts"].run_cycle,
        IntervalTrigger(minutes=15),
        id="charts_cycle",
        name="Charts — market data",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["x-ray"].run_cycle,
        IntervalTrigger(minutes=30),
        id="xray_cycle",
        name="X-Ray — news scan",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["the-scheduler"].run_cycle,
        IntervalTrigger(hours=4),
        id="scheduler_cycle",
        name="The Scheduler — economic calendar",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["cryptid"].run_cycle,
        IntervalTrigger(minutes=30),
        id="cryptid_cycle",
        name="Cryptid — crypto intelligence",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["globe"].run_cycle,
        IntervalTrigger(minutes=30),
        id="globe_cycle",
        name="Globe — macro & forex",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["ape"].run_cycle,
        IntervalTrigger(minutes=30),
        id="ape_cycle",
        name="Ape — Reddit sentiment",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["headlines"].run_cycle,
        IntervalTrigger(minutes=15),
        id="headlines_cycle",
        name="Headlines — news analysis",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["the-accountant"].run_cycle,
        IntervalTrigger(hours=4),
        id="accountant_cycle",
        name="The Accountant — fundamentals",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["recon"].run_cycle,
        IntervalTrigger(hours=1),
        id="recon_cycle",
        name="Recon — alternative data",
        replace_existing=True,
    )
    # Dept 2 — Análisis
    # Mood Ring runs 5 min after Charts/Headlines so signals have time to propagate
    scheduler.add_job(
        AGENTS["mood-ring"].run_cycle,
        IntervalTrigger(minutes=15),
        id="mood_ring_cycle",
        name="Mood Ring — sentiment fusion",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["pattern-master"].run_cycle,
        IntervalTrigger(minutes=15),
        id="pattern_master_cycle",
        name="Pattern Master — setup scanner",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["the-bridge"].run_cycle,
        IntervalTrigger(minutes=30),
        id="bridge_cycle",
        name="The Bridge — cross-asset correlations",
        replace_existing=True,
    )
    # Bull and Bear are on-demand (triggered via bus messages) — no fixed schedule
    # Dept 3 — Estrategia
    scheduler.add_job(
        AGENTS["the-architect"].run_cycle,
        IntervalTrigger(hours=4),
        id="architect_cycle",
        name="The Architect — strategy synthesis",
        replace_existing=True,
    )
    # The Scribe runs right after Architect (triggered by bus messages, cycle is a flush)
    scheduler.add_job(
        AGENTS["the-scribe"].run_cycle,
        IntervalTrigger(hours=4),
        id="scribe_cycle",
        name="The Scribe — report writing",
        replace_existing=True,
    )
    # Dept 4 — Decisión y Riesgo (event-driven keepalives)
    scheduler.add_job(
        AGENTS["the-shield"].run_cycle,
        IntervalTrigger(minutes=30),
        id="shield_cycle",
        name="The Shield — risk watchdog",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["the-boss"].run_cycle,
        IntervalTrigger(minutes=30),
        id="boss_cycle",
        name="The Boss — decision watchdog",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["the-messenger"].run_cycle,
        IntervalTrigger(minutes=15),
        id="messenger_cycle",
        name="The Messenger — pending signals check",
        replace_existing=True,
    )
    # Dept 5 — Ejecución
    scheduler.add_job(
        AGENTS["the-watchdog"].run_cycle,
        IntervalTrigger(minutes=5),
        id="watchdog_cycle",
        name="The Watchdog — position monitor",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["the-trigger"].run_cycle,
        IntervalTrigger(minutes=30),
        id="trigger_cycle",
        name="The Trigger — order status check",
        replace_existing=True,
    )
    # Dept 6 — Aprendizaje
    scheduler.add_job(
        AGENTS["the-historian"].run_cycle,
        IntervalTrigger(hours=1),
        id="historian_cycle",
        name="The Historian — performance stats",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["the-professor"].run_cycle,
        IntervalTrigger(hours=24),
        id="professor_cycle",
        name="The Professor — weekly post-mortem",
        replace_existing=True,
    )
    # Special / Meta
    scheduler.add_job(
        AGENTS["tokin"].run_cycle,
        IntervalTrigger(hours=1),
        id="tokin_cycle",
        name="Tokin — budget watchdog",
        replace_existing=True,
    )
    scheduler.add_job(
        AGENTS["maverick"].run_cycle,
        IntervalTrigger(hours=6),
        id="maverick_cycle",
        name="Maverick — lateral connections",
        replace_existing=True,
    )
    # Eleventh Man is purely event-driven — no scheduled cycle

    scheduler.start()
    log.info("[Brain] Scheduler running — %d jobs registered", len(scheduler.get_jobs()))

    # Run first cycle immediately on startup
    log.info("[Brain] Running initial agent cycles...")
    asyncio.create_task(run_initial_cycles())

    log.info("[Brain] Ready on http://0.0.0.0:%d", settings.port)

    yield  # ← server runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
    for agent in AGENTS.values():
        await agent.stop()
    await bridge.stop()
    await bus.disconnect()
    log.info("[Brain] Shutdown complete")


async def run_initial_cycles() -> None:
    """Run each agent once on startup so data is immediately available.

    Dept 1 runs first, then we pause so their signals propagate on the bus
    before Dept 2 agents try to fuse/analyze them.
    """
    await asyncio.sleep(3)  # Wait for bus + pubsub to be ready

    dept1 = ["charts", "x-ray", "the-scheduler", "cryptid", "globe",
             "ape", "headlines", "the-accountant", "recon"]
    dept2 = ["mood-ring", "pattern-master", "the-bridge"]
    dept3 = ["the-architect", "the-scribe"]
    dept4 = ["the-shield", "the-boss", "the-messenger"]
    # Bull, Bear are on-demand — no initial cycle needed

    for name in dept1:
        try:
            log.info("[Brain] Initial cycle: %s", name)
            await AGENTS[name].run_cycle()
            await asyncio.sleep(4)  # Stagger yfinance calls — free tier rate limit
        except Exception as exc:
            log.error("[Brain] Initial cycle error (%s): %s", name, exc)

    # Give Dept 1 signals time to propagate through the bus
    log.info("[Brain] Dept 1 complete — waiting 5s for signals to propagate...")
    await asyncio.sleep(5)

    for name in dept2:
        try:
            log.info("[Brain] Initial cycle: %s", name)
            await AGENTS[name].run_cycle()
        except Exception as exc:
            log.error("[Brain] Initial cycle error (%s): %s", name, exc)

    # Dept 3 runs after Dept 2 has published analysis signals
    log.info("[Brain] Dept 2 complete — waiting 5s before strategy layer...")
    await asyncio.sleep(5)

    for name in dept3:
        try:
            log.info("[Brain] Initial cycle: %s", name)
            await AGENTS[name].run_cycle()
        except Exception as exc:
            log.error("[Brain] Initial cycle error (%s): %s", name, exc)

    # Dept 4 + 5 start listening immediately — purely event-driven
    for name in [*dept4, "the-trigger", "the-watchdog"]:
        log.info("[Brain] %s online — listening on bus", name)


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="TradingAICenter Brain",
    version="0.1.0",
    description="Multi-agent trading analysis engine",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Claw-Empire is on the same Docker network
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health & status ────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents": len(AGENTS),
        "version": "0.1.0",
    }


@app.get("/agents")
async def list_agents():
    return {
        "agents": [
            {
                "id": agent.agent_id,
                "name": agent.agent_name,
                "department": agent.department,
                "emoji": agent.emoji,
                "status": agent.status.value,
                "current_task": agent.current_task,
            }
            for agent in AGENTS.values()
        ]
    }


@app.get("/agents/{agent_id}/status")
async def agent_status(agent_id: str):
    agent = AGENTS.get(agent_id)
    if not agent:
        return {"error": "Agent not found"}, 404
    return {
        "id": agent.agent_id,
        "name": agent.agent_name,
        "status": agent.status.value,
        "current_task": agent.current_task,
    }


@app.post("/api/brain/approval")
async def handle_approval(body: dict):
    """UI posts user approval decisions here (APPROVE / REJECT / WAIT / MODIFY)."""
    from knowledge_bus.bus import BusMessage, MessageType, MessageCategory
    msg = BusMessage(
        from_agent="ui",
        to_agent="the-messenger",
        type=MessageType.DIRECT_MESSAGE,
        category=MessageCategory.SYSTEM,
        payload={"type": "approval_response", **body},
        priority=1,
    )
    await bus.publish(msg)
    return {"received": True, "ticker": body.get("ticker"), "decision": body.get("decision")}


@app.post("/agents/{agent_id}/run")
async def trigger_agent(agent_id: str):
    """Manually trigger an agent cycle (for testing)."""
    agent = AGENTS.get(agent_id)
    if not agent:
        return {"error": "Agent not found"}
    asyncio.create_task(agent.run_cycle())
    return {"triggered": agent_id, "at": datetime.now(timezone.utc).isoformat()}


# ── Knowledge Bus REST interface ───────────────────────────────────────────────

@app.get("/bus/messages")
async def get_bus_messages(count: int = 50):
    """Return recent messages from the Knowledge Bus (for UI polling)."""
    messages = await bus.get_recent_messages(count=min(count, 200))
    return {"messages": [m.model_dump() for m in messages]}


# ── WebSocket — real-time stream for external clients ─────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.append(ws)
    log.info("[Brain WS] Client connected — total: %d", len(_ws_clients))
    try:
        while True:
            await ws.receive_text()  # Keep-alive; client can send pings
    except WebSocketDisconnect:
        _ws_clients.remove(ws)
        log.info("[Brain WS] Client disconnected — total: %d", len(_ws_clients))


# ── Scheduler jobs status ──────────────────────────────────────────────────────

@app.get("/scheduler/jobs")
async def list_jobs():
    return {
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time),
            }
            for job in scheduler.get_jobs()
        ]
    }
