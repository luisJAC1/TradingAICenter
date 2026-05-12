# TradingAICenter — Agent Roster
> 26 agents across 6 departments + 2 special agents + 1 meta-system watchdog  
> Print-friendly reference. Last updated: 2026-04-14

---

## Legend
| Field | Meaning |
|-------|---------|
| `id` | DB slug used in code |
| Role | `lead` = team_leader · `sr` = senior · `jr` = junior |
| Schedule | When this agent runs |
| Bus | What it publishes → Knowledge Bus |
| Power | Unique capability or rule |

---

# DEPT 1 — RESEARCH `research` 🔍
> Underground Jungle · 9 agents · Gather raw intelligence from all markets

---

### 1.1 · X-Ray 🛰️
| | |
|---|---|
| `id` | `x_ray` |
| Role | Senior |
| Schedule | 24/7 (skeleton crew) |
| Sources | Twitter/X API v2 · StockGeist · snscrape · GDELT · Google News RSS |
| Bus | `social_signal` · `political_alert` · `sentiment_spike` |
| Power | Tracks 10 world leaders (Trump, Xi, Powell, Musk, etc.) — connects their tweets to market impact with historical precedent |

---

### 1.2 · The Scheduler 📅
| | |
|---|---|
| `id` | `the_scheduler` |
| Role | Senior |
| Schedule | 24/7 (skeleton crew) |
| Sources | Finnhub Economic Calendar · Alpha Vantage · Forex News API · EODHD |
| Bus | `calendar_event` · `pre_event_alert` · `earnings_incoming` |
| Power | Knows every scheduled event globally — earnings, central bank meetings, elections, OPEC, OpEx. Pre-event analysis with historical avg market reactions |

---

### 1.3 · Headlines 📰
| | |
|---|---|
| `id` | `headlines` |
| Role | Senior |
| Schedule | Every 15 min (market hours) · Every 1h (off-hours) |
| Sources | Finnhub Market News · Alpha Vantage News · NewsAPI.ai · Yahoo Finance · Google News RSS |
| Bus | `news_event` · `macro_alert` · `geopolitical_risk` |
| Power | Multi-order effect analysis (1st → 2nd → 3rd order). Covers M&A, sanctions, wars, AI regulation, climate policy |

---

### 1.4 · Charts 📈
| | |
|---|---|
| `id` | `charts` |
| Role | Senior |
| Schedule | Every 5 min (market hours) · Every 1h (off-hours) |
| Sources | Alpaca Market Data · Alpha Vantage Technical · yfinance · TA-Lib (local) |
| Bus | `ohlcv_update` · `pattern_detected` · `indicator_signal` |
| Power | 20+ indicators across 7 timeframes (5m/15m/1H/4H/D/W/M). **Rule: NEVER presents a setup without stop-loss. Min R:R 1:2** |

---

### 1.5 · The Accountant 🧮
| | |
|---|---|
| `id` | `the_accountant` |
| Role | Senior |
| Schedule | Every 4h (market hours) · Daily (off-hours) |
| Sources | Financial Modeling Prep · Alpha Vantage · Finnhub · SEC EDGAR · OpenBB |
| Bus | `fundamental_update` · `red_flag_alert` · `valuation_signal` |
| Power | DCF, P/E, P/B, ROE, D/E, insider activity. Has a red-flags checklist: revenue declining + stock rising, insider selling, auditor changes, etc. |

---

### 1.6 · Cryptid 🕸️
| | |
|---|---|
| `id` | `cryptid` |
| Role | Senior |
| Schedule | 24/7 (crypto never sleeps) |
| Sources | CoinGecko · CoinGlass · Etherscan · DeFi Llama · Alternative.me · Alpaca Crypto |
| Bus | `crypto_signal` · `whale_alert` · `defi_update` · `fear_greed` |
| Power | On-chain analysis: whale movements, exchange inflows/outflows, funding rates, stablecoin flows, MEV, L2 adoption. Also tracks crypto regulation by country |

---

### 1.7 · Globe 🌍
| | |
|---|---|
| `id` | `globe` |
| Role | Senior |
| Schedule | 24/7 (skeleton crew) |
| Sources | FXCM demo · Alpha Vantage Forex · OANDA practice · FRED API · Finnhub Forex |
| Bus | `macro_regime` · `forex_signal` · `dxy_update` · `geopolitical_flow` |
| Power | DXY is KING. Tracks macro regimes: Risk-On / Risk-Off / Stagflation / Reflation. Maps global money flows between countries, currencies, and asset classes |

---

### 1.8 · Ape 🦍
| | |
|---|---|
| `id` | `ape` |
| Role | Junior |
| Schedule | Every 30 min (market hours) · Every 2h (off-hours) |
| Sources | Reddit API/PRAW · Finnhub Social · StockGeist · StockTwits · Polymarket · Kalshi |
| Bus | `retail_sentiment` · `meme_alert` · `prediction_market` |
| Power | Monitors 9 subreddits (WSB, r/stocks, r/crypto, etc.). **Key insight: retail sentiment is a CONTRARIAN indicator at extremes** |

---

### 1.9 · Recon 🕵️
| | |
|---|---|
| `id` | `recon` |
| Role | Senior |
| Schedule | Every 1h (market hours) · Every 4h (off-hours) |
| Sources | Finnhub · Financial Modeling Prep · Quiver Quantitative · SEC EDGAR · CBOE |
| Bus | `dark_pool_alert` · `unusual_options` · `insider_activity` · `smart_money` |
| Power | Smart money hierarchy: Congressional trading → Dark pool blocks → Unusual options → Insider buying → Short interest → ETF flows |

---

# DEPT 2 — ANALYSIS `analysis` 📊
> Crystal Caves · 5 agents · Process, correlate, and debate

---

### 2.1 · Mood Ring 💎
| | |
|---|---|
| `id` | `mood_ring` |
| Role | Lead |
| Schedule | Every 15 min (market hours) |
| Sources | Consumes all DEPT 1 outputs from Knowledge Bus |
| Bus | `unified_sentiment` · `divergence_alert` |
| Weights | Financial News 25% · Options Flow 20% · Twitter 20% · Reddit 15% · Crypto 10% · Political 10% |
| Power | **Divergences are most valuable**: Smart money bullish + Retail bearish = STRONG BUY signal |

---

### 2.2 · Pattern Master ⭐
| | |
|---|---|
| `id` | `pattern_master` |
| Role | Senior |
| Schedule | Every 15 min (market hours) |
| Sources | Charts' outputs from Knowledge Bus |
| Bus | `setup_signal` · `scored_pattern` |
| Scoring | TF agreement 25% · Volume 20% · Pattern reliability 20% · S/R quality 15% · Indicator confluence 10% · Sentiment 10% |
| Power | Outputs: Entry Zone · Stop-Loss · TP1/TP2/TP3 · R:R · Position size · Invalidation level |

---

### 2.3 · Bull 🐂
| | |
|---|---|
| `id` | `bull` |
| Role | Senior |
| Schedule | On-demand (when Architect calls debate) |
| Sources | All DEPT 1 + 2 outputs |
| Bus | `bull_case` · `debate_round` |
| Power | Presents the STRONGEST case for buying. Must rebut every Bear argument. **Rule: Intellectually honest — if data doesn't support buying, says so** |

---

### 2.4 · Bear 🐻
| | |
|---|---|
| `id` | `bear` |
| Role | Senior |
| Schedule | On-demand (when Architect calls debate) |
| Sources | All DEPT 1 + 2 outputs |
| Bus | `bear_case` · `debate_round` · `risk_warning` |
| Power | "What If" framework: market crash / black swan / earnings miss / sentiment reversal / maximum loss scenario. Must rebut every Bull argument |

---

### 2.5 · The Bridge 🌉
| | |
|---|---|
| `id` | `the_bridge` |
| Role | Senior |
| Schedule | Every 30 min (market hours) |
| Sources | All DEPT 1 outputs + price feeds |
| Bus | `correlation_update` · `broken_correlation_alert` |
| Tracks | DXY↔Gold · Yields↔Growth stocks · Oil↔Airlines · VIX↔S&P500 · BTC↔Nasdaq · USD/JPY↔carry trades · Copper↔global growth |
| Power | **Most valuable signal: when NORMAL correlations BREAK** — that's highest-alpha territory |

---

# DEPT 3 — STRATEGY `strategy` ♟️
> Golden Dungeon · 2 agents · Synthesize into trade plans

---

### 3.1 · The Architect 🏛️
| | |
|---|---|
| `id` | `the_architect` |
| Role | Lead |
| Schedule | Every 4h (market hours) · On-demand (when signal threshold hit) |
| Sources | All DEPT 1 + 2 outputs + Maverick ideas |
| Bus | `trade_plan` · `debate_summary` · `no_trade_decision` |
| Rules | Max 5 open trades · Max 2% risk/trade · Max 6% total portfolio heat · Moderates Bull vs Bear (2–5 rounds) |
| Power | **Can and should say "NO TRADE TODAY"** — sometimes no trade is the best trade |

---

### 3.2 · The Scribe ✍️
| | |
|---|---|
| `id` | `the_scribe` |
| Role | Senior |
| Schedule | After every Architect trade plan |
| Sources | Architect's trade plan + all supporting analysis |
| Bus | `report_ready` · `pdf_generated` · `ppt_generated` |
| Sections | Executive Summary · Market Conditions · Opportunity · Technical Setup · Fundamentals · Sentiment · Risk · Trade Parameters · Bull vs Bear · Agent Consensus · Final Recommendation |
| Power | Visual-first design: traffic-light risk indicators · agent consensus heatmap · Bull vs Bear side-by-side · Progressive depth (30-second read → deep dive) |

---

# DEPT 4 — DECISION `decision` ⚖️
> Boss Chamber · 3 agents · Risk check + final verdict

---

### 4.1 · The Shield 🛡️ ⚠️ VETO POWER
| | |
|---|---|
| `id` | `the_shield` |
| Role | Lead |
| Schedule | Runs on EVERY trade plan before The Boss sees it |
| Bus | `risk_approved` · `risk_vetoed` · `risk_warning` |
| Auto-veto if | Risk >2% · Portfolio heat >6% · 3+ same-sector positions · Stop >2× ATR · Correlation >0.8 with existing position |
| Rules | 50% size reduction before HIGH-impact events · 10% drawdown = circuit breaker |
| Power | **Hard veto — The Boss cannot override The Shield** |

---

### 4.2 · The Boss 👔
| | |
|---|---|
| `id` | `the_boss` |
| Role | Lead |
| Schedule | After Shield approves |
| Sources | Scribe's report + Shield's risk assessment + Eleventh Man's contrarian analysis |
| Bus | `final_verdict` · `conviction_score` |
| Verdicts | STRONG BUY (>80% conviction) · BUY (>65%) · HOLD · SKIP · SELL |
| Power | Final AI decision maker. Explains in plain language. Sees both main recommendation AND contrarian case before deciding |

---

### 4.3 · The Messenger 📲
| | |
|---|---|
| `id` | `the_messenger` |
| Role | Senior |
| Schedule | Always listening · Fires on Boss verdicts + Watchdog alerts |
| Channels | WhatsApp (primary) · Dashboard · Email digest · Desktop notification |
| Bus | `message_sent` · `approval_received` · `approval_timeout` |
| Power | **ONLY agent that touches WhatsApp.** 30-min reminder if no response. Auto-cancels signal at 2h. Exempt from Tokin's veto (safety-critical) |

---

# DEPT 5 — EXECUTION `execution` ⚡
> Lihzahrd Temple · 2 agents · Paper trading + position monitoring

---

### 5.1 · The Trigger ⚡
| | |
|---|---|
| `id` | `the_trigger` |
| Role | Lead |
| Schedule | On human approval only |
| Brokers | Alpaca (stocks + crypto + options) · FXCM demo (forex) · OANDA practice (forex) |
| Bus | `trade_executed` · `order_placed` · `execution_failed` |
| Power | **Executes ONLY after human approval via WhatsApp or Dashboard.** Auto-places stop-loss and take-profit on execution. Paper trading only until proven |

---

### 5.2 · The Watchdog 🐕
| | |
|---|---|
| `id` | `the_watchdog` |
| Role | Senior |
| Schedule | 24/7 (skeleton crew) — monitors all open positions |
| Sources | Real-time price feeds from Alpaca |
| Bus | `position_update` · `stop_hit` · `proximity_alert` · `condition_change` |
| Power | Trailing stops · Real-time P&L · Condition change alerts while waiting for approval. Escalates to human after 24h if position is stuck |

---

# DEPT 6 — LEARNING `learning` 🧪
> Wizard Tower · 2 agents · Learn from every trade

---

### 6.1 · The Historian 📚
| | |
|---|---|
| `id` | `the_historian` |
| Role | Lead |
| Schedule | Daily (off-hours) · On-demand backtesting |
| Frameworks | Backtesting.py · VectorBT PRO · Zipline-Reloaded · NautilusTrader |
| Bus | `backtest_result` · `strategy_performance` · `market_regime_fit` |
| Metrics | Sharpe ratio · Max drawdown · Win rate · Profit factor |
| Power | Identifies which market conditions the system performs best AND worst in |

---

### 6.2 · The Professor 🎓
| | |
|---|---|
| `id` | `the_professor` |
| Role | Senior |
| Schedule | After every closed trade · Weekly summary |
| Storage | SQLite (trade history) + ChromaDB (vector search for similar past situations) |
| Bus | `agent_weight_update` · `leaderboard_update` · `strategy_graveyard` |
| Power | Feedback loop: Trade result → Post-mortem → Adjust agent weights/thresholds → Strategy Graveyard. Runs the Agent Leaderboard (accuracy per agent per market per timeframe) |

---

# SPECIAL AGENTS — Outside Department Structure

---

### S.1 · The Eleventh Man 🎭 ⚠️ MANDATORY CONTRARIAN
| | |
|---|---|
| `id` | `the_eleventh_man` |
| Dept | None (special) |
| Role | Senior |
| Schedule | After every Scribe report, before The Boss decides |
| Bus | `contrarian_case` · `premortem_analysis` |
| Pipeline | Scribe generates report → **Eleventh Man reviews it** → his contrarian analysis appended → Boss sees both |

**Sacred duty:** Based on Israeli intelligence Tenth Man Rule — when 9 of 10 agree, the 10th MUST disagree.

| Consensus level | His response |
|---|---|
| 60% agree | Moderate counter-case |
| 80% agree | Strong counter-case with historical evidence |
| 95%+ agree | **RED ALERT** — this is where he earns his keep |

**Toolkit:** Premortem · Historical analogies · Crowded trade detection · Black swan scan · Survivorship bias check · Narrative deconstruction

**Output includes:** Contrarian confidence score (0–100) + Recommendation: PROCEED WITH CAUTION / REDUCE SIZE / RECONSIDER / ABORT

> If his contrarian case is genuinely weak, he says so honestly — this actually *increases* confidence in the trade.

---

### S.2 · Maverick 🎲
| | |
|---|---|
| `id` | `maverick` |
| Dept | None (special) |
| Role | Junior |
| Schedule | Every 4h (market hours) · Throttled first at 95% budget |
| Bus | `creative_idea` · `lateral_connection` |
| Pipeline | Reads ALL Knowledge Bus → generates ideas → Architect considers them |

**Thinking frameworks:** Lateral connections · 2nd/3rd order effects · Contrarian timing · Structural trades · Shovel sellers · Overreaction plays · Thematic deep cuts

**Idea output:**
```
idea_name · thesis · the_insight · instruments · entry_trigger
risk · reward_potential · creativity_score (1–10) · confidence (0–100)
```

> Least efficient agent (cost/run) — first to be throttled by Tokin. Ideas don't need to be traded to have value.

---

# META-SYSTEM — Tokin 💰 ⚠️ VETO POWER OVER ALL LLM CALLS
| | |
|---|---|
| `id` | `tokin` |
| Dept | None (meta) |
| Role | Lead |
| Schedule | 24/7 sidecar — intercepts every LLM call system-wide |
| Bus | `budget_alert` · `agent_throttled` · `cost_report` |
| Exempt from veto | The Shield · The Messenger (safety-critical) |

**Budget thresholds:**
| Threshold | Action |
|---|---|
| 80% | WhatsApp alert to human |
| 95% | Pause Maverick + Historian. All cycles slow to 8h intervals |
| 100% | **HARD STOP** — all LLM calls blocked until human approves more budget |

**Auto-alerts (no human request):**
- Any agent burns >20% of daily budget in one call (runaway loop)
- Any API hits 90% of its free tier limit
- Cost-per-analysis increases >50% vs previous week
- Every Monday: weekly cost summary

---

# Quick Reference Table

| # | Name | ID | Dept | Role | Schedule | Special Power |
|---|------|----|------|------|----------|---------------|
| 1 | X-Ray | `x_ray` | research | sr | 24/7 | Political leader tweet → market impact |
| 2 | The Scheduler | `the_scheduler` | research | sr | 24/7 | All global scheduled events |
| 3 | Headlines | `headlines` | research | sr | 15m/1h | Multi-order effect analysis |
| 4 | Charts | `charts` | research | sr | 5m/1h | 7 timeframes, always includes stop |
| 5 | The Accountant | `the_accountant` | research | sr | 4h/daily | Red flags checklist |
| 6 | Cryptid | `cryptid` | research | sr | 24/7 | On-chain whale & DeFi analysis |
| 7 | Globe | `globe` | research | sr | 24/7 | DXY + macro regime tracking |
| 8 | Ape | `ape` | research | jr | 30m/2h | Retail sentiment (contrarian at extremes) |
| 9 | Recon | `recon` | research | sr | 1h/4h | Smart money hierarchy |
| 10 | Mood Ring | `mood_ring` | analysis | lead | 15m | Unified sentiment + divergences |
| 11 | Pattern Master | `pattern_master` | analysis | sr | 15m | Scored setups with full parameters |
| 12 | Bull | `bull` | analysis | sr | on-demand | Strongest buy case |
| 13 | Bear | `bear` | analysis | sr | on-demand | Strongest sell/skip case |
| 14 | The Bridge | `the_bridge` | analysis | sr | 30m | Broken correlation = alpha signal |
| 15 | The Architect | `the_architect` | strategy | lead | 4h/on-demand | Moderates debate, builds trade plan |
| 16 | The Scribe | `the_scribe` | strategy | sr | after plan | Visual reports (PDF + PPT) |
| 17 | The Shield | `the_shield` | decision | lead | every trade | **VETO** — hard risk rules |
| 18 | The Boss | `the_boss` | decision | lead | after shield | Final AI verdict |
| 19 | The Messenger | `the_messenger` | decision | sr | always-on | WhatsApp only — human interface |
| 20 | The Trigger | `the_trigger` | execution | lead | on-approval | Human-approved execution only |
| 21 | The Watchdog | `the_watchdog` | execution | sr | 24/7 | Real-time position monitoring |
| 22 | The Historian | `the_historian` | learning | lead | daily | Backtesting all strategies |
| 23 | The Professor | `the_professor` | learning | sr | after trade | Adjusts weights, runs leaderboard |
| 24 | The Eleventh Man | `the_eleventh_man` | special | sr | after scribe | **Mandatory contrarian** |
| 25 | Maverick | `maverick` | special | jr | 4h | Creative lateral ideas |
| 26 | Tokin | `tokin` | meta | lead | 24/7 sidecar | **VETO** all LLM calls over budget |

---

# Gamification Levels
| Level | Title | Unlocks |
|---|---|---|
| 1–4 | Intern | Basic analysis tasks |
| 5–9 | Junior | Full pipeline participation |
| 10–14 | Senior | Debate leadership, cross-dept messages |
| 15–19 | Lead | Can hire/spawn new agents |
| 20–24 | Manager | Strategy override suggestions |
| 25+ | Legend | Full autonomy mode (still human-approved) |

XP sources: Correct predictions · Consensus accuracy · Unique signals found · Cost efficiency (Tokin grades each agent)

---

*26 agents total · 6 departments · 2 special · 1 meta · Always human-approved · Paper trading first*
