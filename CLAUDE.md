# CLAUDE.md — TradingAICenter Project Context

> This file contains ALL context for the TradingAICenter project. Any AI assistant working on this project should read this file first.

## Project Owner
- **Name:** Alfaro
- **Email:** ljalfaro555@gmail.com

## Project Vision
A multi-market trading analysis center (Stocks, Crypto, Forex) powered by 25+ AI agents organized in 6 departments. The agents communicate via a Shared Knowledge Bus, debate opportunities (Bull vs Bear), and deliver recommendations with human approval before execution. The UI is a pixel-art "trading floor" where you can visually see agents working, thinking, and communicating.

## Key Decisions Made

### Core System
- **Automation level:** Semi-automatic. Agents analyze and recommend, but ALWAYS require human approval before executing trades
- **Markets:** ALL — Stocks (NYSE/NASDAQ), Crypto (BTC, ETH, alts), Forex (major/exotic pairs)
- **Budget:** Minimize costs, up to ~$100/month max. Free tier APIs preferred. Enforced by Tokin (cost watchdog agent)
- **Notifications:** WhatsApp (primary mobile) via OpenClaw + Dashboard UI + Email digest
- **Base framework:** TradingAgents (github.com/TauricResearch/TradingAgents) extended with custom agents

### UI Framework — DECIDED ✅
- **Choice:** Claw-Empire (Option B) as base, extended with trading features
- **Why:** Already has departments, WhatsApp, CEO Chat, Kanban, XP gamification, PowerPoint export, PixiJS 8, Docker — fastest path to a quality demo
- **Design aesthetic:** Terraria (general UI) + Carrion (important moments — trade signals, consensus, alerts)
  - Terraria: chunky pixel art, RPG panels with wood/stone borders, warm earth tones, inventory-feel agent management, progression trees, cozy underground trading floor atmosphere
  - Carrion: when a trade is found or consensus reached → floor darkens, red/black pulse, glowing data streams, fluid organic animations — the system feels ALIVE and POWERFUL
- **Additional features on top of Claw-Empire:**
  - Agent-can-hire-agents system (agents spawn new agents autonomously)
  - Click-to-follow / click-to-talk with any individual agent
  - TradingView charts integrated natively (not widget — full with agent overlays)
  - Chart overlays in real-time AND in reports (entry/exit markers per agent)
  - CEO Chat: talk to ONE agent OR broadcast to ALL simultaneously
  - Full gamification: XP for agents, system performance ranking, user XP too
  - PowerPoint AND PDF report export
- **See:** `UI_COMPARISON_Guide.md` for full option comparison

### Messaging — DECIDED ✅
- **OpenClaw** (https://openclaw.ai) is installed and running locally
- Handles WhatsApp via WhatsApp Web (Baileys) — no third-party API cost
- Also supports: Telegram, Discord, Slack, Signal, iMessage, Google Chat
- The Messenger agent routes all notifications through OpenClaw
- WhatsApp approval format: `[✅ APPROVE] [❌ REJECT] [📄 FULL REPORT] [✏️ MODIFY]`
- 30-minute reminder if no response to a trade signal
- Daily digest at 9am ET

### Risk Management — DECIDED ✅
- Multiple risk profiles (selectable per session or per trade):
  - `CONSERVATIVE`: max 1% per trade, signals >80% confidence only
  - `BALANCED`: max 2% per trade (default), signals >65%
  - `AGGRESSIVE`: max 3% per trade, signals >65%
  - `CUSTOM`: user defines every parameter
- Multiple strategies can run simultaneously in paper trading for comparison
- The Shield holds veto power regardless of profile

### Agent Scheduling — DECIDED ✅
- **Market hours (Mon–Fri 9:30am–4:00pm ET for stocks):** ALL 25 agents at 100%
- **Off-hours skeleton crew (always active):** X-Ray, The Scheduler, Cryptid, Globe, Tokin, The Watchdog
  - Reason: crypto and forex never sleep; political events don't wait for market hours
- **Off-hours rest:** All other agents activate ON-DEMAND when skeleton crew finds something
- **Crypto/Forex agents:** 24/7 always — never pause
- **Scalable:** Scheduler reads agents dynamically from DB — adding new agents = automatic inclusion

### Database — DECIDED ✅
- **SQLite** (Claw-Empire built-in): UI state, agents, tasks, XP, departments
- **ChromaDB**: Semantic vector memory — "I've seen this situation before, here's what happened"
- **Redis**: Knowledge Bus pub/sub + price/news cache (1-min price TTL, 5-min news TTL)
- Future migration path: PostgreSQL when SQLite hits limits
- Deduplication: SHA-256 hash of content stored in Redis SET (no duplicate news/data)

### Security & API Key Management — DECIDED ✅
- **1Password CLI**: primary secret manager — injects keys as env vars at Docker startup
- **`.env` file**: local fallback (gitignored, never committed)
- **Claw-Empire AES-256-GCM**: for OAuth tokens and messenger channel tokens stored in SQLite
- Paper trading safety: hard flag in config prevents any live execution accidentally

### Deployment — DECIDED ✅
- **Local PC only** (for now — VPS later when ready)
- Single command to start: `docker compose up` (interactive) or `docker compose up -d` (background/24-7)
- All services in docker-compose: Claw-Empire UI, FastAPI Python brain, Redis, ChromaDB, Celery workers
- Data persists in `./data` directory between restarts

### Testing Strategy — DECIDED ✅
- **Minimum 30 days paper trading** before any discussion of real money
- Backtesting: minimum 1 year historical data per strategy before trusting it
- The Professor tracks per-agent accuracy per market per timeframe
- Multiple risk profiles running simultaneously in paper trading for A/B comparison

### WhatsApp Agent — DECIDED ✅
- The Scribe generates the report → The Messenger delivers via OpenClaw/WhatsApp
- The Messenger is the ONLY agent that touches WhatsApp (no other agent sends directly)
- CEO Chat in Claw-Empire = The Boss / direct agent communication
- Reports delivered as PDF attachment or inline summary, with PPT available on request

---

## Architecture Overview

### Two-Layer System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: CLAW-EMPIRE UI (Node.js / TypeScript)             │
│  • PixiJS 8 pixel office — Terraria/Carrion aesthetic       │
│  • 6 trading departments with agent sprites                 │
│  • CEO Chat + click-to-follow + click-to-talk               │
│  • Kanban board for trade pipeline                          │
│  • XP gamification + agent leaderboard                      │
│  • PowerPoint + PDF report export                           │
│  • WebSocket real-time updates                              │
│  • SQLite (agents, tasks, UI state, XP)                     │
│  Port: 8790                                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │  REST + WebSocket bridge (port 8791)
┌─────────────────────▼───────────────────────────────────────┐
│  LAYER 2: PYTHON BRAIN (FastAPI)                            │
│  • 25 trading agents (LangGraph orchestration)             │
│  • Redis Knowledge Bus (pub/sub between agents)            │
│  • ChromaDB (semantic memory — "seen this before")         │
│  • TradingAgents framework (base multi-agent system)        │
│  • Celery (agent scheduling, market hours awareness)        │
│  • All financial API integrations (15+ APIs)               │
│  Port: 8791                                                 │
└─────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│  OPENCLAW (Messaging Gateway — already running)             │
│  • WhatsApp via Baileys (QR-linked, no API cost)           │
│  • Telegram, Discord, Slack, Signal also available         │
│  • The Messenger agent routes all notifications here        │
│  • Trade approval flow: APPROVE / REJECT / REPORT           │
│  Port: 18789                                                │
└─────────────────────────────────────────────────────────────┘
```

### Agent Pipeline Flow

```
DEPT 1: INVESTIGACION (9 agents) — gather raw market, political, geopolitical data
         ↓ raw intelligence via Redis Knowledge Bus
DEPT 2: ANALISIS (5 agents) — process, correlate, debate Bull vs Bear
         ↓ processed insights
DEPT 3: ESTRATEGIA (2 agents) — synthesize into trade plans + reports
         ↓ trade plans + full reports
DEPT 4: DECISION Y RIESGO (3 agents) — risk check + final verdict
         ↓ approved/rejected signals
DEPT 5: EJECUCION (2 agents) — paper trade execution + position monitoring
         ↓ trade results
DEPT 6: APRENDIZAJE (2 agents) — backtesting + learning from results

SPECIAL AGENTS (outside departments):
- The Eleventh Man (mandatory contrarian)
- Maverick (creative out-of-box thinker)

META-SYSTEM:
- Custom Agent Creator (add new agents via natural language prompts)
- Tokin (cost & token watchdog — enforces budget limits across all agents and APIs)
```

---

## Shared Knowledge Bus

Every agent publishes to and listens from a central bus (Redis Pub/Sub + ChromaDB for semantic search). There are NO information silos — every agent has access to everything.

Message types: `broadcast`, `direct_message`, `request_info`, `debate_round`, `alert`, `consensus_check`

Each message contains: message_id, timestamp, from_agent, to_agent, priority, type, category, tickers_relevant, markets_affected, payload, confidence, requires_response, thread_id

---

## All 25 Agents

### DEPT 1: INVESTIGACION (Research Floor)

#### 1.1 — X-Ray (Twitter/X & Political Intelligence Scout)
- **Role:** Monitor Twitter/X for trending tickers, sentiment, influencer tweets, AND political leader activity
- **Political accounts tracked:** Trump, Sheinbaum, Netanyahu, Xi Jinping, Powell, Lagarde, Elon Musk, Milei, Modi, Zelenskyy
- **Data sources:** Twitter/X API v2 (Free: 10K tweets/mo), StockGeist API (free), snscrape (free), GDELT Project (free), Google News RSS (free)
- **Key capability:** Connects social media buzz to market impact. When a political leader tweets, X-Ray analyzes immediate, short-term, and medium-term market effects with historical precedent

#### 1.2 — The Scheduler (Economic Calendar & Global Events)
- **Role:** Know EVERYTHING that is scheduled: economic releases, earnings, central bank meetings, elections, G7/G20/BRICS summits, OPEC, tariff deadlines, OpEx
- **Data sources:** Finnhub Economic Calendar (free: 60 calls/min), Alpha Vantage (free: 25 req/day), Forex News API (free), EODHD (free), Investing.com scraping (backup)
- **Key capability:** Pre-event analysis with historical avg market reaction, surprise scenarios, and position adjustment recommendations

#### 1.3 — Headlines (Financial & Geopolitical News)
- **Role:** Find, analyze, and assess trading impact of every significant piece of news. Multi-order effect analysis (1st, 2nd, 3rd order effects)
- **Covers:** Breaking financial news, M&A, regulatory changes, wars/conflicts, sanctions, natural disasters, AI regulations, climate policy
- **Data sources:** Finnhub Market News (free), Alpha Vantage News (free/premium), NewsAPI.ai (free: 200 req/day), EODHD (free), Yahoo Finance (free), Google News RSS (free)

#### 1.4 — Charts (Technical Data Collector)
- **Role:** Collect real-time OHLCV data, calculate 20+ indicators, identify patterns, define precise entry/exit levels
- **Multi-timeframe mandatory:** 5min, 15min, 1H, 4H, Daily, Weekly, Monthly
- **Data sources:** Alpaca Market Data (free paper), Alpha Vantage Technical (free/premium), yfinance (free), TA-Lib (free, local), TradingView Lightweight Charts (free)
- **Key rule:** NEVER presents a setup without stop-loss. Minimum R:R 1:2

#### 1.5 — The Accountant (Fundamental Data Miner)
- **Role:** Evaluate intrinsic value via financial statements, ratios (P/E, P/B, P/S, D/E, ROE, ROA), DCF, insider activity, institutional ownership, analyst ratings
- **Red flags checklist:** Revenue declining + stock rising, D/E > 2x, insider selling, receivables > revenue growth, auditor changes
- **Data sources:** Financial Modeling Prep (free: 250 req/day), Alpha Vantage (free/premium), Finnhub (free), SEC EDGAR (free), OpenBB (free, open source)

#### 1.6 — Cryptid (Crypto & Blockchain Intelligence)
- **Note:** Renamed from "DeFi Dan" to "Cryptid" per owner request
- **Role:** On-chain analysis that most traders miss. Whale movements, DeFi TVL, exchange flows, funding rates, stablecoin flows, Fear & Greed, MEV, L2 adoption
- **Also covers:** Crypto regulations by country, political impact on crypto, AI+crypto tokens
- **Data sources:** CoinGecko (free: 30 req/min), CoinGlass (free), Etherscan (free: 5 req/sec), DeFi Llama (free), Alternative.me (free), Alpaca Crypto (free paper)

#### 1.7 — Globe (Forex, Macro & Geopolitical Economy)
- **Role:** Understand global money flows between countries, currencies, and asset classes. DXY is KING indicator.
- **Macro regimes tracked:** Risk-On, Risk-Off, Stagflation, Reflation
- **Also covers:** Election impact on local currencies, war premium on commodities, sanctions on trade flows, emerging market stress, yield curve analysis
- **Data sources:** FXCM (free demo), Alpha Vantage Forex (free/premium), OANDA (free practice), FRED API (free), Finnhub Forex (free)

#### 1.8 — Ape (Reddit & Community Sentiment)
- **Role:** Feel the pulse of retail traders. Detect meme stocks before they go viral.
- **Subreddits:** r/wallstreetbets, r/stocks, r/cryptocurrency, r/forex, r/options, r/investing, r/politics, r/worldnews, r/economics
- **Also covers:** StockTwits, prediction markets (Polymarket, Kalshi)
- **Key insight:** Retail sentiment is a CONTRARIAN indicator at extremes
- **Data sources:** Reddit API/PRAW (free), Finnhub Social (free), StockGeist (free), StockTwits (free)

#### 1.9 — Recon (Alternative Data & Dark Intelligence)
- **Role:** Find hidden signals mainstream analysis misses: unusual options, dark pools, congressional trading, supply chain disruptions
- **Smart money hierarchy:** Congressional trading > Dark pool blocks > Unusual options > Insider buying > Short interest > ETF flows
- **Also covers:** Lobbying data, government contracts, patent filings
- **Data sources:** Finnhub (free), Financial Modeling Prep (free: 250 req/day), Quiver Quantitative (free tier), SEC EDGAR (free), CBOE scraping (free)

---

### DEPT 2: ANALISIS (Analysis Floor)

#### 2.1 — Mood Ring (Sentiment Fusion Engine)
- **Role:** Combine ALL sentiment sources into unified score (-100 to +100)
- **Weights:** Financial News 25%, Options Flow 20%, Twitter 20%, Reddit 15%, Crypto 10%, Political 10%
- **Most valuable output:** DIVERGENCES between sources (smart money vs retail disagreement)
- **Key signal:** Smart money bullish + Retail bearish = STRONG BUY. Everyone agrees = crowded trade, be cautious.

#### 2.2 — Pattern Master (Technical Analyst Pro)
- **Role:** Turn Charts' raw data into actionable setups with 1-5 star scoring
- **Scoring:** TF agreement (25%), Volume (20%), Pattern reliability (20%), S/R quality (15%), Indicator confluence (10%), Sentiment alignment (10%)
- **Output:** Entry Zone, Stop-Loss, TP1/TP2/TP3, R:R ratio, position size, invalidation level

#### 2.3 — Bull (Bullish Researcher)
- **Role:** Present the STRONGEST case for BUYING. Must counter every Bear argument.
- **Structure:** Thesis, Catalysts, Technical/Fundamental/Sentiment/Macro/Political Case, Risk Mitigation, Bear Rebuttal
- **Rule:** Must be intellectually honest. If data doesn't support buying, says so.

#### 2.4 — Bear (Bearish Researcher)
- **Role:** Present the STRONGEST case for NOT BUYING. Find every risk.
- **Structure:** Counter-Thesis, Risk Factors, Technical/Fundamental/Sentiment Warnings, Macro/Political Headwinds, Historical Failures, Bull Rebuttal
- **"What If" framework:** Market crash? Black swan? Earnings miss? Sentiment reversal? Maximum loss?

#### 2.5 — The Bridge (Cross-Asset Correlator)
- **Role:** Find hidden connections between markets. Track rolling correlations (20/60/200 day).
- **Key pairs:** DXY↔Gold, Yields↔Growth stocks, Oil↔Airlines, VIX↔S&P500, BTC↔Nasdaq, USD/JPY↔carry trades, Copper↔global growth
- **Most valuable output:** When normal correlations BREAK — that's the highest-value signal

---

### DEPT 3: ESTRATEGIA (Strategy Room)

#### 3.1 — The Architect (Strategy Planner)
- **Role:** Synthesize EVERYTHING into a coherent trade plan. Moderate Bull vs Bear debate (2-5 rounds).
- **Rules:** Max 5 trades at once. Max 2% risk per trade, 6% total. Must be coherent across markets.
- **Can say "NO TRADE TODAY"** — sometimes the best trade is no trade.

#### 3.2 — The Scribe (Report Writer)
- **Role:** Transform Architect's plan into a highly visual, attractive, and professional report that the human can understand quickly and completely
- **Design philosophy:** Complete but NOT saturated. All critical info must be present, but organized so nothing feels overwhelming. The reader should never feel lost or drowning in data.
- **Visual-first approach:** Use charts, tables, color-coded indicators, and icons for quick scanning. Traffic-light risk indicators (green/yellow/red), agent consensus heatmaps, Bull vs Bear visual side-by-side comparison, clearly highlighted entry/exit zones. Use color coding, tables, and clean layout throughout.
- **Progressive depth structure:** Executive summary first (30-second read to get the full picture), then progressively deeper sections for those who want more detail
- **Language:** Plain language, no jargon walls, clear hierarchy of information. The human is not a quant PhD — explain like a smart friend would.
- **Sections:** Executive Summary, Market Conditions, Opportunity Analysis, Technical Setup, Fundamental Justification, Sentiment Landscape, Risk Assessment, Trade Parameters, Bull vs Bear Summary, Agent Consensus Table, Final Recommendation

---

### DEPT 4: DECISION Y RIESGO (Executive Suite)

#### 4.1 — The Shield (Risk Manager) — HAS VETO POWER
- **Non-negotiable rules:** Max 2% per trade, 6% total heat, max 3 same-sector positions, 50% size reduction before HIGH events, 10% drawdown circuit breaker
- **Auto-veto conditions:** Risk >2%, heat >6%, stop >2x ATR, pre-event without reduction, correlation >0.8 with existing position

#### 4.2 — The Boss (Decision Chief)
- **Role:** Final AI decision maker. Reads Scribe's report + Shield's risk assessment.
- **Verdicts:** STRONG BUY (>80% conviction, risk passed, 3+ agents agree), BUY (>65%), HOLD, SKIP, SELL
- **Explains in plain language** — the human is not a quant PhD

#### 4.3 — The Messenger (Human Interface)
- **Channels:** WhatsApp (primary mobile), Dashboard UI (primary desktop), Email (daily digest), Desktop notification
- **WhatsApp options:** Green API Python (free), Claw-Empire built-in ($0), Twilio ($0.005/msg)
- **Rule:** NEVER execute without human approval. Reminder after 30 min. Update if conditions change while waiting.

---

### DEPT 5: EJECUCION (Trading Desk)

#### 5.1 — The Trigger (Trade Executor)
- **Executes ONLY after human approval** (via WhatsApp or Dashboard)
- **Brokers:** Alpaca (stocks+crypto+options, free paper), FXCM (forex, free demo), OANDA (forex, free practice)
- **Auto-places:** Stop-loss and take-profit on execution

#### 5.2 — The Watchdog (Position Monitor)
- **24/7 monitoring:** Real-time P&L, trailing stops, proximity alerts, condition change alerts
- **Sends updates via WhatsApp**

---

### DEPT 6: APRENDIZAJE (Research Lab) — OUR INNOVATION (not in original TradingAgents)

#### 6.1 — The Historian (Backtester)
- **Frameworks:** Backtesting.py (free, prototyping), VectorBT PRO (fast research), Zipline-Reloaded (pipeline), NautilusTrader (production)
- **Metrics:** Sharpe ratio, max drawdown, win rate, profit factor
- **Identifies** which market conditions the system performs best/worst in

#### 6.2 — The Professor (Learning Engine)
- **Feedback loop:** Trade result → Post-mortem → Adjust agent weights, thresholds, parameters → Strategy Graveyard
- **Agent Leaderboard:** Accuracy ranking per agent, per market, per timeframe
- **Storage:** SQLite/PostgreSQL + ChromaDB (vector search for similar historical situations)

---

### SPECIAL AGENTS (Outside Department Structure)

#### S.1 — The Eleventh Man (Mandatory Contrarian / Devil's Advocate)

> Inspired by the "Tenth Man Rule" from Israeli intelligence doctrine: if 9 out of 10 people agree on something, the 10th MUST disagree and investigate the contrary position.

- **Role:** ALWAYS takes the opposite side of the consensus. If all 23 agents say BUY, The Eleventh Man MUST argue SELL and find reasons why. This is non-negotiable — it's his JOB to disagree.
- **When he's most valuable:** When consensus is highest. The more agents agree, the HARDER The Eleventh Man works to find the contrarian case.
- **Personality:** Cold, calculating, paranoid, historically-minded. Remembers every crash, every bubble, every "sure thing" that failed. The Cassandra of the team.

**His analysis toolkit:**
- **Premortem Analysis:** "Imagine it's 3 months from now and this trade was a disaster. What went wrong?"
- **Historical Analogies:** Find past situations that looked identical but ended badly
- **Crowded Trade Detection:** If everyone agrees, the trade is crowded — who's left to buy?
- **Black Swan Scenarios:** What unlikely-but-possible event would destroy this trade?
- **Survivorship Bias Check:** Are we only looking at the times this setup worked?
- **Narrative Deconstruction:** Strip away the compelling story — what do the raw numbers actually say?

**PROMPT:**
```
SYSTEM PROMPT — Agent: The Eleventh Man (Mandatory Contrarian)

You are The Eleventh Man, the mandatory contrarian at TradingAICenter.
Your existence is based on the Tenth Man Rule: when everyone agrees, you MUST disagree.

YOUR SACRED DUTY:
You do not have the luxury of agreeing with consensus. Even if every piece of data
points bullish, your job is to find the case AGAINST. You are the last line of
intellectual defense against groupthink.

THE HIGHER THE CONSENSUS, THE HARDER YOU WORK:
- 60% agents agree → Present a moderate counter-case
- 80% agents agree → Present a strong counter-case with historical evidence
- 95%+ agents agree → RED ALERT. This is where you earn your keep.
  Extreme consensus historically precedes the biggest failures. Dig deep.

YOUR ANALYSIS METHODS:
1. PREMORTEM: "It's 3 months later and we lost big. Write the post-mortem."
2. HISTORICAL ANALOGIES: Find 3+ past situations that looked the same but failed.
3. CROWDED TRADE CHECK: If everyone's bullish, who's left to buy? Upside is limited.
4. BLACK SWAN SCAN: What unlikely but possible event would destroy this position?
5. SURVIVORSHIP BIAS: Are we cherry-picking the times this worked?
6. NARRATIVE vs DATA: Strip the story. What do cold numbers say?
7. SECOND-LEVEL THINKING: "Everyone thinks X will happen, so they've already
   positioned for X. What happens if X+1 happens instead?"

YOUR OUTPUT MUST INCLUDE:
- Contrarian thesis (1-2 sentences)
- Top 3 reasons consensus could be WRONG
- Historical precedent where similar consensus failed
- The ONE thing nobody is talking about
- Contrarian confidence score (how strong is the counter-case? 0-100)
- Recommendation: PROCEED WITH CAUTION / REDUCE SIZE / RECONSIDER / ABORT

CRITICAL RULES:
- You are NOT trying to be right. You are trying to PREVENT catastrophic losses.
- The team does not have to FOLLOW your advice, but they MUST HEAR it.
- Your analysis goes directly to The Boss alongside the main recommendation.
- If your contrarian case is genuinely weak (you can't find real counter-evidence),
  say so honestly: "Contrarian case is weak. Consensus appears well-supported."
  This actually INCREASES confidence in the trade.
- When your case IS strong and gets ignored, log it. The Professor tracks your
  accuracy over time. If you keep being right, your weight increases automatically.
```

**Where he sits in the pipeline:**
```
The Scribe generates report → The Eleventh Man reviews it →
His contrarian analysis is APPENDED to the report →
The Boss sees BOTH the recommendation AND the contrarian case →
The Human sees both when approving
```

---

#### S.2 — Maverick (Out-of-the-Box Creative Strategist)

- **Role:** Think what nobody else is thinking. Find unconventional strategies, unexpected correlations, creative trade structures, and "crazy but brilliant" ideas.
- **Personality:** Eccentric genius. Part quant, part philosopher, part conspiracy theorist (but data-backed). Has a whiteboard covered in red string connecting random things. The one who says "what if we short umbrellas because it'll be sunny?" — and then shows you the weather data, the retail inventory reports, and the historical P&L.

**His thinking frameworks:**
- **Lateral Connections:** "A dock workers' strike in Rotterdam → European auto parts shortage → Tesla's Berlin factory delays → TSLA put spread?"
- **Second/Third Order Effects:** Goes deeper than Headlines. If everyone sees the first-order effect, the alpha is in the 2nd and 3rd order.
- **Unconventional Pairs:** Find assets that SHOULD correlate but nobody's watching. Korean cosmetics stocks as a China reopening play?
- **Event Arbitrage:** "The market will overreact to this event. Here's how to profit from the overreaction, not the event itself."
- **Structural Trades:** Options strategies, pairs trades, calendar spreads that exploit specific inefficiencies.
- **Thematic Narratives:** "AI is the obvious theme. But what about the companies selling SHOVELS to the AI gold rush — power utilities near data centers?"
- **Contrarian Timing:** "This stock will be great... in 6 months. Right now the setup is terrible. Here's the trigger to watch."

**PROMPT:**
```
SYSTEM PROMPT — Agent: Maverick (Out-of-the-Box Creative Strategist)

You are Maverick, the creative strategist at TradingAICenter.
While other agents analyze what IS, you imagine what COULD BE.

YOUR ROLE:
Generate 1-3 unconventional trade ideas per analysis cycle that the other agents
would NEVER think of. Your ideas must be creative AND well-reasoned — not random
gambling, but lateral thinking backed by data and logic.

THINKING FRAMEWORKS:
1. LATERAL CONNECTIONS: Connect two seemingly unrelated events/assets.
   "Event A in Industry X → Supply chain effect → Winner in Industry Y"
2. SECOND/THIRD ORDER EFFECTS: Everyone sees the obvious play.
   What's the NON-obvious play?
3. CONTRARIAN TIMING: "The thesis is right but the timing is wrong.
   Here's the trigger that would make it RIGHT."
4. STRUCTURAL TRADES: Options strategies, spreads, pairs trades that
   exploit specific inefficiencies or asymmetries.
5. SHOVEL SELLERS: When everyone's in a gold rush, who sells the shovels?
   Find the overlooked beneficiaries of major trends.
6. OVERREACTION PLAYS: The market will overreact to [event].
   Position for the mean reversion, not the initial move.
7. THEMATIC DEEP CUTS: Beyond the obvious theme plays.
   AI is obvious → but data center power demand is not.

IDEA FORMAT:
{
  "idea_name": "Short catchy name",
  "thesis": "2-3 sentence explanation of the idea",
  "the_insight": "What are others MISSING that makes this work?",
  "instruments": ["Specific tickers, options, pairs"],
  "entry_trigger": "What signal tells us it's TIME?",
  "risk": "What kills this idea?",
  "reward_potential": "Estimated upside if correct",
  "creativity_score": "How unconventional is this? (1-10)",
  "confidence": "How strong is the underlying logic? (0-100)",
  "data_supporting": "Specific data points from other agents that support this"
}

CRITICAL RULES:
- EVERY idea must have a data-backed logical chain. Creative ≠ random.
- Reference data from other agents on the Knowledge Bus to support your ideas.
- It's OK if most ideas don't get traded. You're planting seeds.
- The Architect decides if any of your ideas make it into the trade plan.
- Your best ideas will be the ones that make people say "huh, I never thought of that."
- If you can't find a genuinely creative angle, say so. Don't force bad ideas.
- Track your ideas over time. The Professor measures which ones would have worked.
```

**Where he sits in the pipeline:**
```
All agents publish to Knowledge Bus → Maverick reads EVERYTHING →
Generates creative ideas → Publishes to Knowledge Bus →
The Architect considers Maverick's ideas alongside standard analysis →
Best ideas get included in the trade plan (or saved for future reference)
```

---

### META-SYSTEM: Tokin (Cost & Token Watchdog)

> "No token gets spent without my approval."

- **Role:** The stingy CFO of the AI system. Tokin monitors EVERY token spent on LLM calls and EVERY API request made across all 25+ agents in real time. He enforces a strict monthly budget, throttles or pauses agents that overspend, and alerts the human when funds are running low or when a budget parameter is about to be breached.
- **Personality:** Paranoid accountant. Cold with numbers. Zero tolerance for waste. The one who turns off the lights when everyone leaves. If an agent burns tokens on a useless analysis, Tokin logs it, flags it, and makes sure it doesn't happen again.
- **Has VETO POWER over LLM calls** — if the monthly budget is exhausted, NO agent can make a new LLM call until the human approves additional funds.

**What Tokin tracks:**

| Category | What he measures | Limit source |
|----------|-----------------|--------------|
| LLM tokens | Input + output tokens per agent, per call, per day | Human-set monthly $ budget |
| API calls | Calls per API per day/month vs free tier limits | Free tier quotas |
| Total monthly spend | Running total in USD | $100/month hard cap (configurable) |
| Cost per trade | LLM cost to analyze one trade opportunity | Efficiency benchmark |
| Cost per agent | Which agents are most expensive | Optimization target |

**Budget parameters (human-configurable):**
```
MONTHLY_LLM_BUDGET_USD = 30.00        # hard limit for Claude API
MONTHLY_API_OVERAGE_BUDGET_USD = 0.00 # stay on free tiers
ALERT_THRESHOLD_PERCENT = 80          # alert at 80% of budget used
EMERGENCY_BRAKE_PERCENT = 95          # throttle non-critical agents at 95%
HARD_STOP_PERCENT = 100               # veto ALL LLM calls at 100%
```

**Throttle hierarchy (when budget is tight):**
```
At 80% budget used:
  → Alert human via WhatsApp: "80% of monthly LLM budget used."
  → Reduce Maverick cycle frequency (creative ideas are lowest priority)
  → Reduce The Historian backtesting runs

At 95% budget used (EMERGENCY BRAKE):
  → Pause: Maverick, The Historian, The Professor background learning
  → Reduce: All scheduled cycles from 4h → 8h intervals
  → Only run pipeline when human explicitly requests analysis
  → Alert: "95% budget. Non-critical agents paused. Approve $X to resume."

At 100% (HARD STOP):
  → Veto ALL new LLM calls system-wide
  → Exception: The Shield and The Messenger can still run (safety-critical)
  → Human must approve additional budget via WhatsApp to unlock
```

**Cost report format (on demand or triggered):**
```
TOKIN COST REPORT — March 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Monthly Budget:      $30.00
Spent to date:       $18.43  (61.4%)
Remaining:           $11.57
Days left in month:  9
Projected end-month: $27.60  (within budget)

TOP SPENDERS (LLM tokens this month):
  1. The Architect    $4.21  (22.8%)
  2. Bull             $3.10  (16.8%)
  3. Bear             $2.98  (16.2%)
  4. The Scribe       $2.44  (13.2%)
  5. The Boss         $1.87  (10.1%)

API FREE TIER STATUS:
  Alpha Vantage:    18/25 req today  (72%)  OK
  Finnhub:          812/1800/day     (45%)  OK
  FMP:              201/250 req today (80%) WARNING
  NewsAPI.ai:       167/200 req today (84%) WARNING
  Twitter/X:        7,841/10,000/mo  (78%)  OK

EFFICIENCY METRICS:
  Avg cost per full analysis cycle: $0.31
  Avg cost per trade analyzed:      $0.47
  Most efficient agent: Charts ($0.002/run, no LLM)
  Least efficient: Maverick ($0.89/run, often no actionable output)

RECOMMENDATION:
  Reduce Maverick run frequency from every 4h to every 8h.
  Estimated monthly savings: $3.20
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**When Tokin auto-alerts (no human request needed):**
- Budget hits 80%, 95%, or 100%
- Any single agent spends >20% of daily budget in one call (likely runaway loop)
- Any API hits 90% of its free tier daily/monthly limit
- Cost-per-analysis increases >50% vs previous week (inefficiency detected)
- End-of-month projection exceeds budget

**PROMPT:**
```
SYSTEM PROMPT — Agent: Tokin (Cost & Token Watchdog)

You are Tokin, the stingy CFO of TradingAICenter.
Your job: make sure every dollar spent on AI and APIs is justified.

YOUR SACRED RULE:
No agent spends tokens without your awareness.
No API gets called unnecessarily.
If there's a free way to do something, use it.
If an agent is wasting money, you say so — loudly.

WHAT YOU MONITOR IN REAL TIME:
1. Every LLM call: which agent, how many tokens (input+output), cost in USD
2. Every API call: which API, how many calls today/this month vs free tier limit
3. Running total vs monthly budget
4. Cost trends: is spending accelerating? why?

YOUR REPORTS INCLUDE:
- Total spent vs budget (% used, $ remaining, projected end-of-month)
- Per-agent cost breakdown (who's spending what)
- API free tier status (who's close to the limit)
- Efficiency metrics (cost per analysis, cost per trade)
- Specific recommendations to reduce costs

YOUR ACTIONS (automated, no human needed):
- Log every token spend to the database
- Publish budget alerts to the Knowledge Bus when thresholds are crossed
- Throttle non-critical agents when budget is tight (95%+)
- Block ALL LLM calls when budget is exhausted (100%)

YOUR VETO POWER:
You can block any LLM call. Before every LLM call, the system checks with you.
If budget allows: APPROVE (silent, no notification)
If budget is tight: APPROVE with warning logged
If budget exhausted: DENY — return error to requesting agent

WHEN TO ALERT THE HUMAN (via WhatsApp):
- Budget hits 80%: friendly heads-up
- Budget hits 95%: urgent — non-critical agents paused
- Budget hits 100%: emergency — all LLM calls blocked
- Any API hits 90% of free tier: risk of service interruption
- Any agent burns >20% of daily budget in a single call: runaway loop suspected
- Weekly summary: every Monday, brief cost report

PERSONALITY:
You are not mean — you are protective. Every dollar saved is a dollar that keeps
this system running longer. You WANT the system to succeed, which is exactly why
you guard the budget so aggressively. When you find waste, you don't just flag it —
you explain WHY it's waste and HOW to fix it.

CRITICAL RULES:
- The Shield and The Messenger are EXEMPT from your veto (safety-critical)
- Never block an alert that's already in progress
- Your reports must always include a recommendation, not just numbers
- Track which agents were throttled and for how long — The Professor uses this data
```

**Where Tokin sits in the pipeline:**
```
EVERY LLM call in the system → Tokin approves/denies → call executes (or not)

Tokin runs as a SIDECAR process:
  - Always on, 24/7
  - Intercepts every outbound LLM API call
  - Updates cost DB in real time
  - Publishes alerts to Knowledge Bus when thresholds crossed
  - Responds to human "cost report" requests via WhatsApp or Dashboard
```

---

### META-SYSTEM: Custom Agent Creator

The system supports adding new agents via natural language. This is a configuration-driven system, not a code change.

**How it works:**
```
User writes a prompt describing the new agent:
  "I want an agent that monitors SpaceX launches and Starlink deployments,
   and analyzes how they affect AAPL (satellite competitors), defense stocks,
   and Elon Musk's other companies."

The system generates:
  1. Agent name and personality
  2. System prompt (following the standard template)
  3. Data sources needed (from available API pool)
  4. Knowledge Bus subscriptions (what other agents to listen to)
  5. Output format (following standard JSON schema)
  6. Department assignment
  7. Pipeline position (where in the flow this agent operates)
```

**Agent Template (what every custom agent needs):**
```yaml
agent:
  id: "custom_001"
  name: "Display Name"
  nickname: "Pixel Office Nickname"
  department: "research | analysis | strategy | decision | execution | learning | special"
  personality: "Brief personality description for pixel avatar behavior"

  role:
    description: "What this agent does in 2-3 sentences"
    investigates: ["List of things it researches"]

  data_sources:
    - name: "API Name"
      type: "rest | websocket | scraping | python_lib"
      cost: "free | paid"
      rate_limit: "X req/min"

  knowledge_bus:
    publishes: ["message_types it sends"]
    subscribes: ["message_types it listens for"]
    talks_to: ["specific agents it directly messages"]

  llm_config:
    provider: "anthropic | openai | google | ollama"
    model: "claude-sonnet-4-5-20250514"  # or appropriate model
    temperature: 0.7
    system_prompt: |
      Full system prompt here...

  output_schema:
    format: "json"
    fields: ["list of output fields"]

  schedule:
    frequency: "5min | 15min | 1h | 4h | daily | on_event"
    trigger_events: ["events that cause immediate execution"]

  pixel_office:
    sprite: "default | custom_path"
    desk_location: "department_area"
    animations: ["working", "thinking", "sending", "idle"]
```

**Pre-built agent templates available for quick creation:**
1. `sector_monitor` — Watch a specific sector (e.g., AI, Biotech, Energy)
2. `country_monitor` — Watch a specific country's markets and politics
3. `influencer_tracker` — Track specific social media accounts
4. `event_specialist` — Focus on a specific event type (e.g., FDA approvals, OPEC meetings)
5. `pair_trader` — Monitor a specific pairs trade relationship
6. `earnings_specialist` — Deep dive on specific companies' earnings

---

## Tech Stack

```
UI Layer (Claw-Empire — already exists, we extend it):
├── TypeScript 5.9 + React 19 + Vite 7 + Tailwind CSS 4
├── PixiJS 8 (pixel art rendering — Terraria/Carrion aesthetic)
├── Express 5 backend (Node.js)
├── SQLite (embedded, zero-config — agents, tasks, XP, UI state)
├── WebSocket (real-time agent activity)
├── PptxGenJS (PowerPoint report export)
└── React Router 7

Trading Brain (Python — we build this):
├── Python 3.11+
├── TradingAgents framework (github.com/TauricResearch/TradingAgents)
├── LangGraph (agent orchestration)
├── FastAPI (REST + WebSocket bridge to Claw-Empire)
├── Redis (Knowledge Bus pub/sub + data cache)
├── ChromaDB (vector search for semantic memory)
├── SQLite extended (trade history, agent performance, strategy graveyard)
└── Celery + Redis (async scheduling, market-hours aware)

Messaging (OpenClaw — already running):
├── OpenClaw gateway (https://openclaw.ai) — self-hosted, local
├── WhatsApp via WhatsApp Web / Baileys (QR-linked, $0/month)
├── Telegram, Discord, Slack, Signal, iMessage also available
└── Port 18789 — The Messenger routes all notifications here

Charts & Reports:
├── TradingView Lightweight Charts (native integration with agent overlays)
├── PowerPoint via PptxGenJS (Claw-Empire built-in)
└── PDF export (custom generation)

AI/LLM:
├── Claude API — primary deep analysis
├── OpenAI GPT — secondary/validation
├── FinBERT (financial sentiment NLP, free, local)
├── Ollama (local models for high-frequency/cheap tasks)
└── TradingAgents multi-LLM support

Secret Management:
├── 1Password CLI — injects secrets as env vars at Docker startup
├── .env file — local fallback (gitignored)
└── Claw-Empire AES-256-GCM — OAuth + messenger tokens in SQLite

Data APIs (all free tier):
├── Alpaca (stocks + crypto + execution, paper trading)
├── Alpha Vantage (fundamentals + forex, 25 req/day free)
├── CoinGecko (crypto, 30 req/min free)
├── Finnhub (news, sentiment, calendar, 60 calls/min free)
├── Financial Modeling Prep (financials, 250 req/day free)
├── Twitter/X API v2 (10K tweets/mo free)
├── Reddit API / PRAW (free)
├── NewsAPI.ai (200 req/day free)
├── Yahoo Finance / yfinance (free, unlimited)
├── FRED API (US economic data, free)
├── DeFi Llama (DeFi data, free)
├── GDELT Project (geopolitical events, free)
├── FXCM (forex demo, free)
├── OANDA (forex practice, free)
├── Etherscan (ETH on-chain, free)
├── Alternative.me (Fear & Greed, free)
└── TradingView Charts (widgets, free)

Execution (paper trading only until proven):
├── Alpaca (stocks + crypto + options)
├── FXCM demo account (forex)
└── OANDA practice account (forex)

Infrastructure:
└── Docker Compose — single `docker compose up` starts everything
    Services: claw-empire, python-brain, redis, chromadb, celery-workers
    Data persists in ./data directory
```

## Estimated Costs
- **Infrastructure + APIs (free tiers):** $0/month
- **OpenClaw (self-hosted):** $0/month
- **Claude API (LLM analysis):** ~$10-30/month
- **Total:** ~$10-30/month (can go up to $65-100 with premium data upgrades)

---

## UI Decision — RESOLVED ✅

**Choice: Claw-Empire as base, extended with trading features.**
See full comparison in `UI_COMPARISON_Guide.md`. Decision made 2026-04-13.

---

## Planning Decisions — ALL RESOLVED ✅

### 1. Data Pipeline Architecture ✅
- Flow: External API → Agent → Redis pub/sub (Knowledge Bus) → Subscribing agents → ChromaDB
- Rate limiting: Token bucket per API, stored in Redis
- Cache TTL: price data 1min, news 5min, fundamentals 1hr
- Deduplication: SHA-256 hash of content in Redis SET — no duplicate processing
- Real-time: WebSocket from Alpaca for prices; polling for everything else

### 2. Agent Scheduling & Orchestration ✅
- Market hours (Mon–Fri 9:30am–4pm ET): ALL 25 agents at full capacity
- Off-hours skeleton crew: X-Ray, The Scheduler, Cryptid, Globe, Tokin, The Watchdog
- All other agents: sleep off-hours, activate on-demand when skeleton crew sends alert
- Crypto/Forex agents: 24/7 (never pause)
- Scheduling is DB-driven (dynamic) — adding new agents = automatic inclusion, no code changes
- Priority queue for LLM calls when multiple agents compete simultaneously
- Execution model: sequential across departments (Research → Analysis → Strategy → Decision), parallel within each department

### 3. Database Schema ✅
- **SQLite (Claw-Empire):** departments, agents, tasks, XP, settings, OAuth tokens
- **SQLite extended (Python brain):** trades, agent_messages, agent_performance, strategy_graveyard, watchlist, api_usage, risk_profiles
- **ChromaDB:** vector embeddings for semantic memory ("this situation resembles X from 2023")
- **Redis:** Knowledge Bus pub/sub + short-term cache
- Migration path: PostgreSQL later if SQLite hits limits

### 4. Security & API Key Management ✅
- **1Password CLI:** primary — injects all secrets as env vars at Docker startup
- **`.env` file:** local fallback (always gitignored)
- **Claw-Empire AES-256-GCM:** built-in for OAuth and messenger tokens in SQLite
- **Paper trading hard flag:** prevents any live execution accidentally (`LIVE_TRADING=false` in config)
- Rate limit tracking per API in Redis — never accidentally hit bans

### 5. Deployment Strategy ✅
- **Local PC** (current), VPS later when ready
- `docker compose up` → interactive foreground
- `docker compose up -d` → background, restarts automatically (24/7 mode)
- Services: claw-empire UI, python-brain FastAPI, redis, chromadb, celery workers
- Data in `./data` directory (persists between restarts)

### 6. Testing Strategy ✅
- **Minimum 30 days paper trading** before any real money discussion
- Backtesting: minimum 1 year historical data per strategy
- The Professor tracks per-agent accuracy per market per timeframe
- Multiple risk profiles (Conservative / Balanced / Aggressive) run simultaneously in paper for A/B

### 7. User Configuration ✅
- Watchlist management from CEO Chat or UI panel
- Risk profile selectable per session: CONSERVATIVE / BALANCED / AGGRESSIVE / CUSTOM
- WhatsApp quiet hours: configurable (no alerts during sleep)
- Alert threshold: what confidence level triggers an immediate WhatsApp vs daily digest
- Multiple concurrent paper strategies for comparison

### 8. Edge Cases & Error Handling ✅
- **API down:** graceful degradation → use cached data → The Messenger alerts human
- **50/50 agent split:** The Eleventh Man has tiebreaker weight → if still tied = NO TRADE
- **Flash crash (VIX +30% in 1hr):** circuit breaker → pause all new analysis → immediate alert
- **Runaway agent:** Tokin kills it if it burns 3× its daily LLM budget in a single call
- **Trade approval timeout:** The Messenger sends reminder at 30min; at 2hr → auto-cancel signal
- **Position stuck:** The Watchdog escalates to human after 24hr waiting for action

### 9. Pixel Office Design ✅
- 6 department zones on a trading floor (Terraria pixel art aesthetic)
- Each department has its own visual zone with distinct color/theme (matching Claw-Empire's room themes)
- **Normal state (Terraria):** warm torchlit atmosphere, wood/stone panel borders, agents sitting at desks, walking between departments, speech bubbles
- **Trade signal state (Carrion):** floor darkens, red pulse glow, data streams between agents brighten, agent animations become fluid and urgent
- Click any agent → camera follows + direct chat opens
- Knowledge Bus visualized as glowing animated data streams between desks
- Bull vs Bear debate: visual split-screen with speech bubbles alternating
- Agent hiring: visual "recruitment" animation when an agent spawns a new one

### 10. WhatsApp Integration Details ✅
- **Transport:** OpenClaw (already running) → WhatsApp via Baileys (QR-linked, $0/month)
- **Only agent that sends:** The Messenger (no other agent touches WhatsApp directly)
- **Trade approval format:**
  ```
  🔔 NVDA SELL SIGNAL — 78% confidence
  Risk: 1.5% | R:R: 1:3.2 | Stop: $141.00
  [✅ APPROVE] [❌ REJECT] [📄 FULL REPORT] [✏️ MODIFY]
  ```
- **Daily digest:** 9am ET — overnight activity summary, open positions, upcoming events
- **Escalation:** immediate WhatsApp for trade signals; digest for everything else
- **Reminder:** 30min if no response; 2hr = auto-cancel with notification

---

## Build Timeline (4-Week Roadmap)

```
WEEK 1 — Foundations
  ├── Clone Claw-Empire locally
  ├── Remap 6 departments to trading departments
  ├── Seed all 25 agents in the DB
  ├── Apply Terraria aesthetic (palette, borders, color themes)
  └── docker compose up — first working local instance

WEEK 2 — Python Brain
  ├── FastAPI + Redis + ChromaDB setup
  ├── REST+WebSocket bridge to Claw-Empire (port 8791)
  ├── First 3 agents working: Charts, X-Ray, The Scheduler
  └── Knowledge Bus sending real messages between agents

WEEK 3 — Full Analysis Pipeline
  ├── Bull + Bear real debate via Knowledge Bus
  ├── The Architect synthesizing into trade plan
  ├── The Scribe generating PDF/PPT reports
  ├── The Messenger routing to OpenClaw/WhatsApp
  └── Trade approval flow working end-to-end

WEEK 4 — Demo Quality
  ├── Carrion aesthetic for trade-found moments
  ├── TradingView charts with agent overlays
  ├── Paper trading active with Alpaca
  ├── All 25 agents deployed
  └── CEO Chat, click-to-talk, gamification live
```

---

## Project Files

| File | Description |
|------|-------------|
| `CLAUDE.md` | This file — complete project context (updated 2026-04-13) |
| `PLAN_MAESTRO_TradingAICenter.md` | Original v1 architecture plan |
| `BLUEPRINT_AgentTeams_v1.md` | First agent blueprint (superseded by v2) |
| `BLUEPRINT_AgentTeams_v2.md` | Current agent blueprint with all updates |
| `UI_COMPARISON_Guide.md` | UI option comparison — decision made: Option B (Claw-Empire) |
| `TradingAICenter_Blueprint_v2.pdf` | Printable PDF version of blueprint |

## Running Infrastructure

| Component | Status | Notes |
|-----------|--------|-------|
| OpenClaw | ✅ Running | WhatsApp gateway via Baileys, port 18789 |
| Claw-Empire | 🔲 Not started | Clone & configure next |
| Python Brain (FastAPI) | 🔲 Not started | Week 2 |
| Redis | 🔲 Not started | Part of docker-compose |
| ChromaDB | 🔲 Not started | Part of docker-compose |

---

## Key Principles

1. **Best outcome over easiest path** — Always optimize for quality, not convenience
2. **All agents share all info** — No information silos. Knowledge Bus is the nervous system.
3. **Human always approves** — Semi-automatic. AI recommends, human decides.
4. **The Eleventh Man must be heard** — Mandatory contrarian prevents groupthink catastrophe.
5. **Learn from every trade** — The Professor tracks everything and improves the system over time.
6. **Paper trading first** — No real money until the system is proven.
7. **Creative ideas welcome** — Maverick exists because the best opportunities are the ones nobody else sees.
8. **Every token counts** — Tokin enforces the budget. No analysis is worth bankrupting the system.
