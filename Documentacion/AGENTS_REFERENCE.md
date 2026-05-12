# TradingAICenter — Agent Roster Reference

> All 26 V1 agents coded, wired, and running as of 2026-05-04. Smoke test passed.
> Agent IDs and counts live in `config/agents.json`.

## Implementation Summary

| Dept | Agents | LLM calls | Status |
|------|--------|-----------|--------|
| 1 — Research | 9 | Haiku (headlines, xray) | ✅ Running |
| 2 — Analysis | 5 | Haiku (mood, patterns) · Sonnet (bull, bear) | ✅ Running |
| 3 — Strategy | 2 | Sonnet (architect) · Sonnet (scribe) | ✅ Running |
| 4 — Decision | 3 | None (shield) · Haiku borderline only (boss) · None (messenger) | ✅ Running |
| 5 — Execution | 2 | None | ✅ Running |
| 6 — Learning | 2 | Haiku weekly (professor) · None (historian) | ✅ Running |
| Special | 4 | Sonnet (eleventh man) · Haiku (maverick) · None (tokin) | ✅ Running |

---

## Dept 1 — Research · 9 agents ✅ Complete

| Agent | Role | Schedule |
|-------|------|----------|
| X-Ray 🛰️ | Twitter/X sentiment + political leader tracking | 24/7 |
| The Scheduler 📅 | Forward calendar: earnings, FOMC, G7, OpEx | 24/7 |
| Headlines 📰 | Breaking news, multi-order effects | 15m / 1h |
| Charts 📈 | OHLCV + 20 indicators, 5m–monthly, enforces "The Rule" | 5m / 1h |
| The Accountant 🧮 | Fundamentals: P/E, DCF, insider activity | 4h / daily |
| Cryptid 🕸️ | On-chain: whale movements, DeFi TVL, funding rates | 24/7 |
| Globe 🌍 | Forex/macro: DXY, yield curve, risk-on/off regimes | 24/7 |
| Ape 🦍 | Reddit/WSB retail sentiment — contrarian at extremes | 30m / 2h |
| Recon 🕵️ | Dark pools, unusual options, insider filings | 1h / 4h |

---

## Dept 2 — Analysis · 5 agents 🔄 In progress

| Agent | Role | Schedule |
|-------|------|----------|
| Mood Ring 💎 | Fuses all sentiment → −100→+100; divergences = top signal | 15m |
| Pattern Master ⭐ | 1–5 star setups; entry / stop / TP1 / TP2 / TP3 / R:R | 15m |
| Bull 🐂 | Strongest buy case | On demand |
| Bear 🐻 | Strongest skip/sell case | On demand |
| The Bridge 🌉 | Cross-asset correlations (20/60/200d); breaks = alpha | 30m |

---

## Dept 3 — Strategy · 2 agents

| Agent | Role | Schedule |
|-------|------|----------|
| The Architect 🏛️ | Synthesizes all depts; moderates Bull/Bear; max 5 trades | 4h / on-demand |
| The Scribe ✍️ | Human-facing report + weekly System Improvement Report | After Architect |

---

## Dept 4 — Decision · 3 agents

| Agent | Role | Schedule |
|-------|------|----------|
| The Shield 🛡️ | **VETO.** 2%/trade, 6% heat, 50% pre-events, 10% drawdown breaker | Every trade |
| The Boss 👔 | Final verdict: STRONG BUY / BUY / HOLD / SKIP / SELL | After Shield |
| The Messenger 📲 | **Only WhatsApp agent.** Via OpenClaw. 2h timeout = auto-cancel | 24/7 |

---

## Dept 5 — Execution · 2 agents

| Agent | Role | Schedule |
|-------|------|----------|
| The Trigger ⚡ | Executes **only on human approval**; auto-places stop + TP | Approval only |
| The Watchdog 🐕 | 24/7 P&L monitor, trailing stops, condition alerts | 24/7 |

---

## Dept 6 — Learning · 2 agents

| Agent | Role | Schedule |
|-------|------|----------|
| The Historian 📚 | Backtesting (Backtesting.py → VectorBT); Sharpe, win rate | Daily |
| The Professor 🎓 | Post-mortem → adjust agent weights; Agent Leaderboard | After trade |

---

## Special + Meta · 4 agents

| Agent | Role | Notes |
|-------|------|-------|
| The Eleventh Man 🎭 | **Mandatory contrarian.** Higher consensus = harder he works. | Sits between Scribe and Boss |
| Maverick 🎲 | Lateral connections, 2nd/3rd-order effects | Throttled first when budget tight |
| Tokin 💰 | **VETO over LLM calls.** $30/mo soft cap; hard-stops at 100% | Shield + Messenger exempt |
| Custom Agent Creator | Runtime agent spawner | On demand |

---

## Off-Hours Skeleton Crew

Active when markets are closed: X-Ray · The Scheduler · Cryptid · Globe · Tokin · The Watchdog · The Messenger

---

## V2 Roadmap — 35 agents

Full V2 roster (9 new agents + 8 V1 enhancements, 4 build phases):
`Documentacion/AGENT_ROSTER_V2.html` — open in browser, Ctrl+P for printable version.

**New V2 agents:** The Greek · The Storm · The Oracle · The Scout · The Joker · The Auditor · Questlog · The Librarian · The Cartographer
