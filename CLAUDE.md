# CLAUDE.md — TradingAICenter · Owner: Alfaro (ljalfaro555@gmail.com)

## Quick Start

> `docker-compose.yml` is in `frontend/`. Use `docker-compose` (v1 CLI), NOT `docker compose`.

```bash
# Rebuild + restart brain only (fast — ~10s)
cd frontend && docker-compose stop brain && docker-compose rm -f brain && docker-compose build brain && docker-compose up -d brain

# Full stack (first time or after UI changes)
cd frontend && docker-compose up --build

# Stop everything
cd frontend && docker-compose down
```

**Env files** (`frontend/` directory):
- `.env.docker` — non-secret config (committed)
- `.env.docker.private` — API keys (gitignored, never commit)

## Current State — 2026-05-12

| Component | State | Port | Notes |
|-----------|-------|------|-------|
| Python Brain | ✅ Running (Alpaca data) | 8791 | 26/26 agents · yfinance replaced |
| Redis | ✅ Running | 6379 | Knowledge Bus |
| ChromaDB | ✅ Running | 8000 | Semantic memory (`_type` warning, harmless) |
| Claw-Empire UI | 🔄 Stopped — rebuild pending | 8790 | New schema + brain endpoints coded |
| OpenClaw | ⏸ Not started | 18789 | WhatsApp gateway (opt-in) |

**Phase 1 ✅ DONE (deployed):** yfinance fully replaced by Alpaca v2 (stocks/ETFs/crypto) + Frankfurter (forex) + ETF proxies for macro instruments. Charts/Globe/The Bridge no longer rate-limited. Pattern Master now gets data → strategy pipeline flows.

**Phase 2 ✅ CODED (awaiting claw-empire rebuild):**
- `brain_decisions` + `brain_bus_events` tables seeded
- New endpoints: `POST /api/brain/decision-inbox`, `GET /api/brain/decisions`, `POST /api/brain/decisions/:id/respond`, `GET /api/brain/bus-events`, `GET /api/brain/status`
- `officeWorkflowPack` forced to `development` on boot (fixes "0/26 agents" — agents are seeded under `development`)
- `current_task` column added to `agents` table for brain status text

**Phase 3 🛠 PLANNED:** Trading-specific UI views — new "Trading" sidebar tab with sub-tabs (Trade Signals · Live Feed · Performance · Watchlist), generic claw-empire features hidden from nav, pixel office preserved as homepage.

## API Keys Status

| Key | Status | Where to add | What it enables |
|-----|--------|-------------|-----------------|
| `ANTHROPIC_API_KEY` | ✅ Set | `.env.docker.private` | All LLM agents |
| `OPENAI_API_KEY` | ✅ Set | `.env.docker.private` | Secondary LLM fallback |
| `FINNHUB_API_KEY` | ✅ Set | `.env.docker.private` | Better news + earnings (Headlines) |
| `ALPACA_API_KEY` | ✅ Set | `.env.docker.private` | Real paper trade execution (Trigger) |
| `ALPACA_SECRET_KEY` | ✅ Set | `.env.docker.private` | Real paper trade execution (Trigger) |

Free APIs (no key needed): yfinance · CoinGecko · Reddit JSON · Alternative.me · Google News RSS

## What's Next

1. **Rebuild claw-empire** — `cd frontend && docker-compose build claw-empire && docker-compose up -d claw-empire`. Verify 26 agents visible + new endpoints return 200.
2. **Execute Phase 3 plan** — see `/home/luisalfaro/.claude/plans/i-want-to-generate-quizzical-riddle.md`. Builds the Trading sidebar tab with 4 sub-tabs.
3. **Watch paper trading** — once UI is wired, let it run 30+ days, approve/reject signals in the new Trade Signals view.
4. **V2 agents** (after 30-day validation) — 9 new agents, 8 V1 enhancements.

## Risk Profile Settings

Set `RISK_PROFILE` in `.env.docker.private` — rebuild brain to apply:

| Profile | Risk/Trade | Max Heat | Max Plans |
|---------|-----------|---------|----------|
| `CONSERVATIVE` | 0.5% | 3% | 3 |
| `BALANCED` ← current | 1.0% | 5% | 5 |
| `AGGRESSIVE` | 2.0% | 6% | 5 |

## Architecture

26 agents share a Redis Knowledge Bus. No information silos. All LLM calls tracked by Tokin.
Signal chain: Research → Analysis → Strategy → [Shield veto?] → Boss verdict → Messenger → **User approves** → Trigger executes → Watchdog monitors

```
Claw-Empire UI  :8790  TypeScript · React · PixiJS 8 · SQLite
      │  REST + WebSocket
Python Brain    :8791  FastAPI · 26 agents · APScheduler · Redis · ChromaDB
      │
OpenClaw        :18789 WhatsApp via Baileys
```

**Non-negotiables:** `LIVE_TRADING=false` always · 30+ days paper trading · Human approves every trade

## Notification Channel

Currently: `NOTIFICATION_CHANNEL=ui` — signals appear in UI Decision Inbox only.
To add WhatsApp later: set `NOTIFICATION_CHANNEL=both` + `WHATSAPP_PHONE=+1...` in `.env.docker.private`

## Agents

26 V1 agents across 6 depts + 4 special. Full roster + schedules:
**`Documentacion/AGENTS_REFERENCE.md`**

Off-hours skeleton crew: X-Ray · Scheduler · Cryptid · Globe · Tokin · Watchdog · Messenger

## LLM Cost Design

- **Haiku** (`analysis_model`) — structured JSON, pattern descriptions, basic scoring. ~$0.001/1K tokens
- **Sonnet** (`reasoning_model`) — Bull/Bear debates, Architect synthesis, Boss borderline calls. ~$0.009/1K tokens
- **Tokin** — hard veto at 100% of `MONTHLY_LLM_BUDGET_USD` (currently $10/mo). Shield + Messenger exempt.
- **Zero-LLM agents** — The Shield, Trigger, Watchdog, Historian, Tokin itself. Pure math/data.

## Key Files

| File | Purpose |
|------|---------|
| `brain/main.py` | FastAPI entry · all 26 agents · APScheduler · approval endpoint |
| `brain/agents/` | All 26 agent files |
| `brain/agents/base.py` | BaseAgent — ask_claude (cached), publish, set_status, Tokin veto hook |
| `brain/market/market_data.py` | **NEW** Unified data router (Alpaca/Frankfurter/CoinGecko) — replaces yfinance |
| `brain/config/settings.py` | All env vars · risk profile logic · notification channel |
| `brain/knowledge_bus/bus.py` | Redis pub/sub backbone · MessageCategory enum |
| `brain/bridge/ui_bridge.py` | Bus → UI REST · forwards agent-status, bus-event, decision-inbox |
| `frontend/server/modules/routes/core/agents/brain-integration.ts` | **EXTENDED** All `/api/brain/*` endpoints (status, decisions, bus-events, respond) |
| `frontend/server/modules/bootstrap/schema/base-schema.ts` | **EXTENDED** `brain_decisions` + `brain_bus_events` tables |
| `frontend/server/modules/bootstrap/schema/seeds.ts` | 26-agent seed · pack force to `development` · `current_task` migration |
| `frontend/docker-compose.yml` | Full stack (5 services + volumes) |
| `frontend/data/brain/` | Historian SQLite DB (historian.db) — must be chmod 777 |
| `Documentacion/AGENTS_REFERENCE.md` | Full agent roster with roles + schedules |
| `Documentacion/AGENT_ROSTER_V2.html` | V2 plan — 35 agents (open in browser) |

## Key Principles

1. Human approves every trade — AI recommends, human decides
2. Knowledge Bus is the nervous system — no silos
3. The Eleventh Man must be heard — prevents groupthink
4. Paper trading first — 30+ days before real money
5. Tokin enforces the budget — no analysis bankrupts the system
6. UI first for notifications — WhatsApp is opt-in, not required
7. Zero LLM where logic suffices — Shield, Watchdog, Trigger, Historian are pure code
