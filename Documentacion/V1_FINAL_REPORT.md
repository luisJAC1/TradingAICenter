# TradingAICenter — V1 Final Report
**Owner:** Alfaro (ljalfaro555@gmail.com) · **Date:** 2026-05-06 · **Status:** LIVE — Paper Trading Phase

---

## Executive Summary

TradingAICenter V1 is a complete, production-ready multi-agent AI trading system. 28 agents span 6 operational departments plus 3 meta-agents. They research markets, debate signals adversarially, synthesize trade plans, enforce risk rules, and execute paper trades via Alpaca — all while you remain the final human approver on every single trade.

**The system is fully built. All 28 agents online. Smoke tests passed. Ready for 30-day paper trading phase.**

---

## System At a Glance

| Component | Status | URL | Purpose |
|-----------|--------|-----|---------|
| Claw-Empire UI | ✅ Ready | localhost:8790 | Your command center |
| Python Brain | ✅ Ready | localhost:8791 | 28 agents + signal pipeline |
| Redis | ✅ Ready | internal:6379 | Knowledge Bus (agent nervous system) |
| ChromaDB | ✅ Ready | internal:8000 | Semantic memory |
| OpenClaw | ✅ Ready | internal:18789 | WhatsApp gateway (opt-in) |

**To start the full stack:**
```bash
cd frontend && docker-compose up --build
```

---

## API Keys Status

| Key | Status | What It Enables |
|-----|--------|-----------------|
| ANTHROPIC_API_KEY | ✅ Set | All LLM agents |
| OPENAI_API_KEY | ✅ Set | Secondary LLM fallback |
| FINNHUB_API_KEY | ✅ Set | Richer news + earnings calendar |
| ALPACA_API_KEY | ✅ Set | Paper trade execution |
| ALPACA_SECRET_KEY | ✅ Set | Paper trade execution |

All keys configured. LIVE_TRADING is hardlocked to `false`. The system cannot spend real money.

---

## Architecture

```
Claw-Empire UI  :8790  (TypeScript · React · PixiJS · SQLite)
      │  REST + WebSocket
Python Brain    :8791  (FastAPI · 28 agents · APScheduler)
      │
      ├── Redis :6379   (Knowledge Bus — pub/sub backbone)
      ├── ChromaDB :8000 (Semantic memory)
      └── OpenClaw :18789 (WhatsApp gateway)
```

### Signal Chain (Research → Your Inbox)

```
[9 Research Agents]  15min–4h cycles
         ↓  market data, news, sentiment, technicals, fundamentals
[5 Analysis Agents]  15min cycles + on-demand
         ↓  sentiment fusion, setup ratings, Bull/Bear debates
[2 Strategy Agents]  4h cycles
         ↓  synthesized trade plan with Eleventh Man counter-argument
[Shield Agent]       rule-based veto (7 hard rules, zero LLM)
         ↓  approved plan
[Eleventh Man]       mandatory contrarian challenge
         ↓  challenge added to context
[Boss Agent]         final AI scoring (rule-based 0–100, Haiku on borderline)
         ↓  boss_verdict signal
[Messenger Agent]    → UI Decision Inbox (+ optional WhatsApp)
         ↓  YOU APPROVE OR REJECT
[Trigger Agent]      → Alpaca paper trade execution
[Watchdog Agent]     → 5min position monitoring
[Historian Agent]    → SQLite trade log
[Professor Agent]    → weekly leaderboard + post-mortem
```

---

## All 28 Agents

### Department 1 — Research (9 agents)

| Agent | ID | Schedule | Role | LLM? |
|-------|----|----------|------|------|
| Charts | charts | 15min | OHLCV + 20+ indicators, setup detection | No |
| X-Ray | xray | 30min | Google News RSS, political/macro impact | No |
| Scheduler | scheduler_agent | 4h | Economic calendar, earnings, events via Finnhub | No |
| Cryptid | cryptid | 30min | On-chain metrics, Fear & Greed, DeFi TVL | No |
| Globe | globe | 30min | Macro regime (RISK_ON/RISK_OFF/STAGFLATION), forex | No |
| Ape | ape | 30min | Reddit sentiment (5 subreddits), contrarian signals | No |
| Headlines | headlines | 15min | News impact: 1st/2nd/3rd order effects | Haiku |
| The Accountant | the_accountant | 4h | Fundamentals: P/E, ROE, FCF, red flags | Haiku |
| Recon | recon | 1h | Options unusual activity, Form 4 insiders, short squeeze | No |

**Free data sources:** yfinance · CoinGecko · Reddit JSON · Alternative.me · Google News RSS · SEC EDGAR

### Department 2 — Analysis (5 agents)

| Agent | ID | Schedule | Role | LLM? |
|-------|----|----------|------|------|
| Mood Ring | mood_ring | 15min | Fuses all Dept 1 into sentiment score −100 to +100 | Haiku |
| Pattern Master | pattern_master | 15min | Rates setups 1–5 stars, R:R ratio enforcement | Haiku |
| Bull | bull | On-demand | Strongest bullish case for any ticker | Sonnet |
| Bear | bear | On-demand | Strongest bearish case for any ticker | Sonnet |
| The Bridge | the_bridge | 30min | Correlation regime breaks (7 key pairs) | Haiku |

### Department 3 — Strategy (2 agents)

| Agent | ID | Schedule | Role | LLM? |
|-------|----|----------|------|------|
| The Architect | the_architect | 4h | Requests Bull/Bear, synthesizes plan + Eleventh Man check | Sonnet |
| The Scribe | the_scribe | On-demand | Formats signal for inbox + WhatsApp | No |

### Department 4 — Decision & Risk (3 agents)

| Agent | ID | Schedule | Role | LLM? |
|-------|----|----------|------|------|
| The Shield | the_shield | Always-on | 7-rule hard veto (zero LLM, pure math) | **Never** |
| The Boss | the_boss | Always-on | 0–100 score model, Haiku on borderline 50–64 | Haiku (borderline only) |
| The Messenger | the_messenger | Always-on | Delivers to inbox, manages 2h approval window | **Never** |

**Shield's 7 Veto Rules:**
1. risk_pct > limit → VETO
2. portfolio heat > max → VETO
3. active plans >= max → VETO
4. duplicate ticker already open → VETO
5. correlated asset already open → VETO
6. high-impact event within 24h → halve position size
7. pre-event modifier applied → reduced sizing

**Boss Scoring Model (0–100):**
- Architect conviction: 0–40 pts
- Pattern Master stars: 0–20 pts
- Mood Ring alignment: 0–20 pts
- Regime alignment: 0–10 pts
- R:R ratio: 0–10 pts
- Score 80+: STRONG BUY/SHORT (no LLM)
- Score 65–79: BUY/SHORT (no LLM)
- Score 50–64: Haiku call for borderline
- Score <50: SKIP (no LLM)

### Department 5 — Execution (2 agents)

| Agent | ID | Schedule | Role | LLM? |
|-------|----|----------|------|------|
| The Trigger | the_trigger | Always-on | Alpaca paper order execution (market + GTC stop) | **Never** |
| The Watchdog | the_watchdog | 5min | Position monitoring: stops, TPs, flash crashes | **Never** |

**Watchdog checks every 5 minutes:**
- Flash crash (>5% move) → priority 1 alert
- Stop hit → sends close signal to Trigger
- Stop warning (within 20% of stop distance) → alert
- TP1 hit → raises stop to breakeven
- TP2 hit → alert to consider partial close
- TP3 hit → auto-close signal to Trigger
- Emergency drawdown (>10% of portfolio loss) → forced close

### Department 6 — Learning (2 agents)

| Agent | ID | Schedule | Role | LLM? |
|-------|----|----------|------|------|
| The Historian | the_historian | 1h | Records all closed trades to SQLite | **Never** |
| The Professor | the_professor | 24h | Weekly agent leaderboard + post-mortem | Haiku |

**Historian records per trade:** ticker, direction, entry/exit price, qty, P&L%, result (WIN/LOSS/BREAK_EVEN), close_type, conviction, stars, mood_score, regime, full plan JSON.

**Professor publishes weekly:** who's signals lead to wins, what worked, what failed, system improvement suggestions.

### Special / Meta Agents (3 agents)

| Agent | ID | Schedule | Role | LLM? |
|-------|----|----------|------|------|
| The Eleventh Man | the_eleventh_man | On-demand | Mandatory contrarian on every approved plan | Haiku/Sonnet |
| Maverick | maverick | 6h | Lateral thinking, 2nd/3rd order connections | Haiku |
| Tokin | tokin | 1h | Budget watchdog, hard veto authority over all LLM | **Never** |

**Eleventh Man Rule:** If everyone agrees, one agent MUST disagree. Always. The counter-argument lands in Boss's context before final verdict.

**Tokin Thresholds:**
- 80% of budget → throttles Maverick, publishes warning
- 100% of budget → hard veto on ALL non-exempt LLM calls (Shield, Messenger, UIBridge exempt)

---

## LLM Cost Design

| Model | Used For | Cost |
|-------|---------|------|
| Haiku (claude-haiku-4-5) | Headlines, Accountant, Mood Ring, Pattern Master, Bridge, Boss (borderline) | ~$0.001/1K |
| Sonnet (claude-sonnet-4-6) | Bull, Bear, Architect synthesis | ~$0.009/1K |
| Opus | Reserved (not used in V1) | — |

**Prompt caching** enabled on all system messages (~90% cost reduction on repeated calls).
**Monthly target:** $0–30. Hard cap enforced by Tokin at configured `MONTHLY_LLM_BUDGET_USD`.

---

## Risk Profile Settings

Set `RISK_PROFILE` in `frontend/.env.docker.private` — rebuild brain to apply.

| Profile | Risk/Trade | Max Portfolio Heat | Max Simultaneous Plans |
|---------|-----------|-------------------|----------------------|
| CONSERVATIVE | 0.5% | 3% | 3 |
| **BALANCED** ← current | **1.0%** | **5%** | **5** |
| AGGRESSIVE | 2.0% | 6% | 5 |

---

## What You'll See in the UI (localhost:8790)

### Decision Inbox
Every trade signal that passes all 28 agents lands here. You see:
- Ticker, direction (LONG/SHORT), conviction %
- Entry price · Stop-loss · TP1 · TP2 · TP3
- Risk in dollars and % of portfolio
- The Bull thesis vs Bear concerns
- **The Eleventh Man's counter-argument**
- Boss's scoring rationale

Your actions: **APPROVE** · **REJECT** · **WAIT 1H** · **MODIFY SIZE**
Signal auto-cancels after 2 hours if no action.

### Agent Dashboard
All 28 agents visible with live status (IDLE, WORKING, THINKING, SENDING, WAITING, ERROR). See each agent's last cycle time, message count, and next scheduled run.

### Knowledge Bus Feed
Real-time stream of agent messages. Watch Bull debate Bear. Watch Shield veto a risky plan. Watch Eleventh Man challenge the consensus.

### Performance Tracker
Your paper portfolio P&L over time. Win rate. Average win vs average loss. Best and worst trades. Agent leaderboard.

### CEO Chat
Talk to any single agent or broadcast to all 28 simultaneously.

### Settings Panel
Risk profile, monthly LLM budget, notification channel (UI / WhatsApp / both). Live trading toggle — hardlocked OFF.

---

## How to Use the UI — Click by Click

Open your browser to **`http://localhost:8790`**

---

### The Layout

```
┌─────────────────────────────────────────────────────────┐
│  [Header Bar]  View title  🧭 Decisions(N)  👁 Agents  📋 Tasks  ⚙  │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│ Sidebar  │           Main Content Area                 │
│          │                                              │
│ 🏢 Office │                                              │
│ 👥 Agents │                                              │
│ 📚 Library│                                              │
│ 📊 Dashbd │                                              │
│ 📋 Tasks  │                                              │
│ ⚙️ Settings│                                              │
└──────────┴──────────────────────────────────────────────┘
```

---

### The Sidebar (left column)

Click the **lobster CEO icon** at the top of the sidebar to collapse/expand it.

| Icon | View | What you'll see |
|------|------|----------------|
| 🏢 | **Office** | Pixel art office — your agents walking around their departments, live animations, message deliveries flying across the screen |
| 👥 | **Agents** | Full agent roster — every agent card with status, department, last activity. Click any agent to open their detail view |
| 📚 | **Library** | Skills library (Claw-Empire feature — less relevant for trading, but here) |
| 📊 | **Dashboard** | HQ overview — agent counts, task stats, department performance rankings, mission log |
| 📋 | **Tasks** | Task board — Claw-Empire's kanban system. Trade signals appear here as tasks when they come in |
| ⚙️ | **Settings** | Company name, CEO name, language, theme, API keys, gateway settings |

The bottom of the sidebar shows **Department Status** — each department with how many agents are currently working vs total (e.g. `2/9`). This updates live.

The very bottom shows a green pulsing dot when the system is connected to the brain, and `X/28 working` agent count.

---

### The Header Bar (top strip)

These buttons float at the top right. They open modals/panels on top of whatever view you're in:

#### 🧭 Pending Decisions (most important button)
- Shows a **badge with a number** when trade signals are waiting for your approval
- Click it to open the **Decision Inbox modal**
- This is where every Boss-approved trade signal lands
- Each item shows:
  - Which agent sent it and what type of request it is
  - The full signal content (ticker, thesis, risk, entry/stop/TP levels)
  - **Numbered action buttons** — click the number to respond
  - An **"Open Chat"** button to go talk to that agent directly
- To respond to a signal: **click the numbered option button** (e.g. `1. Approve`, `2. Reject`)
- The modal has a **Refresh** button top-right if you want to re-fetch
- Click anywhere outside the modal (or the ✕) to close

#### 👁 Agent Status
- Opens a live panel showing all **actively running agents**
- Shows elapsed time, last action, CLI process info
- You can **stop a running agent** from here if something looks stuck
- Hit Refresh inside the panel to update

#### 📋 Tasks (header shortcut)
- Quick shortcut to open the task panel without switching sidebar view

#### Report History
- Opens a history of past trade signals, closed positions, and performance summaries from Historian

#### Announcement
- Company-wide broadcast area (Claw-Empire feature)

#### Room Manager
- Configure which rooms/departments are visible in the pixel art Office view

#### 🌙/☀️ Theme toggle
- Switches between dark and light mode

---

### The Office View (🏢)

This is the main "alive" view — a PixiJS pixel art scene of your trading office.

- **Each department has a room** — Research, Analysis, Strategy, Decision, Execution, Learning
- **Agent sprites walk around** their rooms when active
- **Message deliveries animate** across the screen when agents communicate (you'll see little envelopes/packages flying from room to room)
- **Click on an agent sprite** to open their detail panel
- The CEO hallway connects everything

This is the view to leave open on a monitor. It shows the system breathing in real time.

---

### The Agents View (👥)

Grid of all 28 agent cards. Each card shows:
- Agent emoji + name
- Department badge
- Current status (IDLE / WORKING / THINKING / SENDING / WAITING / ERROR)
- Last activity timestamp

**Click any agent card** → opens the **Agent Detail panel** (slides in from the right):
- Full agent config and description
- Performance metrics
- Recent messages this agent published to the bus
- A **"Run Now"** button to manually trigger the agent's cycle
- Message history with the agent

---

### The Dashboard View (📊)

HQ stats overview:
- **HUD stats strip** across the top: total agents, active right now, tasks done, completion rate
- **Department performance** bars — which departments are most active
- **Agent leaderboard** — ranked by task completion / signal quality
- **Mission log** — recent system events

Click **"Start Mission"** (the primary CTA button) to create a new task directly.

---

### The Tasks View (📋)

Kanban board with columns: Planned → In Progress → Review → Done

Trade signals from the brain appear here as tasks. You can:
- **Click a task card** to open the full detail view
- See sub-tasks, agent assignments, task history
- Use the **Filter Bar** at the top to filter by department or status

---

### The Decision Inbox — Step by Step

This is the most important interaction in the whole system.

**When a trade signal is ready:**
1. You'll see the **🧭 badge** increment in the header (e.g. `🧭 1`)
2. Click the **🧭 Pending Decisions** button
3. The modal opens showing the pending signal
4. Read the signal content — it includes the full thesis, risk details, and the Eleventh Man's counter-argument
5. Look at the **numbered buttons** at the bottom of each item:
   - **Option 1** → typically Approve / Proceed
   - **Option 2** → typically Reject / Skip
   - Other options may appear (Wait, Modify Size, etc.)
6. Click the number button for your choice
7. The button shows "Sending..." while it processes
8. The item disappears from the inbox when handled
9. If you want to talk to the agent before deciding, click **"Open Chat"** on that item

**If the inbox shows "No pending decisions right now"** — the agents haven't generated a signal yet, or all pending signals have been handled. Check back after the next Architect cycle (~4 hours).

**If the inbox shows "Options are being prepared..."** — the Boss agent is still scoring the signal. Wait a minute and hit Refresh.

---

### The Chat Panel

Accessible from any agent's detail view via "Open Chat", or from a Decision Inbox item.

- **Left panel:** conversation history with that agent
- **Type a message** in the composer at the bottom and hit Enter or the send button
- You can ask the agent questions, request analysis on a specific ticker, or ask for its reasoning
- To broadcast to ALL agents: use the CEO broadcast feature (look for the "broadcast" option in the chat header)

---

### Settings (⚙️)

Tabs inside Settings:
- **General** — company name, CEO name, UI language (EN/KO/JA/ZH), dark/light theme
- **API** — view configured API providers (read-only display of what's in .env.docker.private)
- **Gateway** — OpenClaw WhatsApp gateway config (phone number, enable/disable)
- **CLI** — Claude Code CLI settings (less relevant for trading use)
- **OAuth** — GitHub/OAuth connections

**To change risk profile or LLM budget:** edit `frontend/.env.docker.private` directly, then rebuild the brain. You cannot change these from the UI — they're environment variables.

---

## Your Daily Routine (Paper Trading Phase)

### Morning (~5 minutes)
1. Open `localhost:8790`
2. Check Decision Inbox — any overnight signals?
3. Read each signal: thesis, counter-argument, risk sizing
4. APPROVE or REJECT (you're always in control)

### During the Day (Passive)
Agents work on their own schedules. You don't need to do anything.

**Off-hours skeleton crew (always running):** X-Ray · Scheduler · Cryptid · Globe · Tokin · Watchdog · Messenger

### Weekly (~15 minutes)
- Review paper portfolio performance
- Check Tokin's LLM spend report
- Read Professor's agent leaderboard
- Note patterns: which signals win? Which lose?

### After 30 Days
- Enough data for real signal quality analysis
- Decide if risk profile needs tuning
- Consider V2 agents (9 new, 8 enhanced — see `AGENT_ROSTER_V2.html`)
- Optionally enable Alpaca live trading (requires explicit decision)

---

## Key Files

| File | Purpose |
|------|---------|
| `brain/main.py` | FastAPI entry, all 28 agents, APScheduler, approval endpoint |
| `brain/agents/base.py` | BaseAgent — ask_claude, publish, set_status, Tokin veto hook |
| `brain/agents/` | All 28 individual agent files |
| `brain/config/settings.py` | All env vars, risk profile logic, model assignments |
| `brain/knowledge_bus/bus.py` | Redis pub/sub backbone, MessageCategory enum |
| `brain/bridge/ui_bridge.py` | Bus → UI REST, forwards signals to decision inbox |
| `frontend/docker-compose.yml` | Full stack (5 services + volumes) |
| `frontend/data/brain/historian.db` | SQLite trade log (must be chmod 777) |
| `frontend/.env.docker.private` | All API keys (never commit) |
| `Documentacion/AGENTS_REFERENCE.md` | Agent roster with full schedules |
| `Documentacion/AGENT_ROSTER_V2.html` | V2 plan — 35 agents (open in browser) |

---

## Non-Negotiables

1. **Human approves every trade** — AI recommends, you decide. Always.
2. **Knowledge Bus is the nervous system** — no agent works in a silo.
3. **The Eleventh Man must be heard** — every high-conviction plan gets challenged.
4. **Paper trading first** — 30+ days before real money. No exceptions.
5. **Tokin enforces the budget** — no LLM call can bankrupt the system.
6. **UI first for notifications** — WhatsApp is opt-in, never required.
7. **Zero LLM where logic suffices** — Shield, Watchdog, Trigger, Historian: pure code.

---

## V2 Roadmap (After 30-Day Validation)

9 new agents planned · 8 V1 enhancements · Full details: `Documentacion/AGENT_ROSTER_V2.html`

Highlights:
- Options flow specialist
- Macro regime-aware position sizing
- Backtester agent (replay historical signals)
- Agent-can-hire-agents system
- Full gamification (agent XP, system ranking, user XP)
- **Radar** — UI-only agent that monitors the Redis Knowledge Bus and renders a live message stream panel in the Office view. Shows every agent publish in real time: who sent it, what category, what tickers, confidence score. Like a radar screen for the nervous system.

---

*TradingAICenter V1 — Built with discipline. Runs with intelligence. Controlled by you.*
