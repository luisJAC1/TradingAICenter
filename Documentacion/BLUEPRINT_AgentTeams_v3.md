# TradingAICenter — Blueprint de Equipos de Agentes v3

> **Documento maestro actualizado: 2026-04-13**
> Este documento es la referencia completa y definitiva del sistema. Supersede v1 y v2.

---

## CAMBIOS VS v2

- ✅ **Decisión de UI:** Claw-Empire como base, extendida con features de trading
- ✅ **Estética visual decidida:** Terraria (general) + Carrion (momentos de trade)
- ✅ **Arquitectura de dos capas** documentada: Claw-Empire UI + Python Brain
- ✅ **OpenClaw instalado y corriendo** — reemplaza la integración de WhatsApp custom
- ✅ **Los 10 gaps de planificación resueltos** completamente
- ✅ **Sistema de riesgo personalizable** con múltiples perfiles simultáneos
- ✅ **Agent scheduling 24/7** con skeleton crew off-hours y escalado dinámico
- ✅ **Agente-contrata-agente** — agentes pueden contratar nuevos agentes autónomamente
- ✅ **Click-to-follow / click-to-talk** — interacción directa con cualquier agente
- ✅ **TradingView nativo** con overlays de agentes en charts
- ✅ **Gamificación completa** — XP para agentes, sistema, y usuario
- ✅ **Roadmap de 4 semanas** definido
- ✅ **Database expandida** — SQLite + ChromaDB + Redis (tres capas)
- ✅ **1Password CLI** para manejo de API keys
- ✅ **WhatsApp agent definido:** The Messenger ruta a través de OpenClaw

---

## VISIÓN DEL SISTEMA

Un centro de trading multi-mercado (Stocks, Crypto, Forex) impulsado por 25+ agentes de IA organizados en 6 departamentos. Los agentes se comunican a través de un Shared Knowledge Bus, debaten oportunidades (Bull vs Bear), y entregan recomendaciones con aprobación humana antes de ejecutar.

**La UI es un pixel-art "trading floor"** donde puedes ver visualmente a los agentes trabajando, pensando, y comunicándose — con estética de **Terraria** en el día a día y **Carrion** cuando el sistema encuentra algo importante.

### Principios inamovibles

1. **Mejor resultado sobre camino fácil** — siempre optimizar calidad sobre conveniencia
2. **Todos los agentes comparten toda la info** — sin silos. El Knowledge Bus es el sistema nervioso.
3. **El humano siempre aprueba** — semi-automático. La IA recomienda, Alfaro decide.
4. **The Eleventh Man SIEMPRE debe ser escuchado** — el contrarian previene groupthink catastrófico
5. **Aprender de cada trade** — The Professor trackea todo y mejora el sistema con el tiempo
6. **Paper trading primero** — cero dinero real hasta que el sistema esté probado (mínimo 30 días)
7. **Ideas creativas bienvenidas** — Maverick existe porque las mejores oportunidades son las que nadie más ve
8. **Cada token cuenta** — Tokin hace cumplir el budget. Ningún análisis vale la pena si quiebra el sistema.

---

## ARQUITECTURA DEL SISTEMA

### Capa 1: UI (Claw-Empire — Node.js / TypeScript)

```
┌─────────────────────────────────────────────────────────────────┐
│  CLAW-EMPIRE TRADING FLOOR                                       │
│                                                                   │
│  ┌─ DEPT 1: INVESTIGACIÓN ─┐  ┌─ DEPT 2: ANÁLISIS ───────────┐  │
│  │  [X-Ray] [Scheduler]   │  │  [Mood Ring] [Pattern Master] │  │
│  │  [Headlines] [Charts]  │  │  [Bull] [Bear] [The Bridge]   │  │
│  │  [Accountant] [Cryptid]│  └────────────────────────────────┘  │
│  │  [Globe] [Ape] [Recon] │                                       │
│  └─────────────────────────┘  ┌─ DEPT 3: ESTRATEGIA ──────────┐  │
│                                │  [The Architect] [The Scribe] │  │
│  ┌─ DEPT 4: DEC. Y RIESGO ─┐  └────────────────────────────────┘  │
│  │  [Shield] [Boss]        │                                       │
│  │  [Messenger]            │  ┌─ DEPT 5: EJECUCIÓN ───────────┐  │
│  └─────────────────────────┘  │  [The Trigger] [The Watchdog] │  │
│                                └────────────────────────────────┘  │
│  ┌─ DEPT 6: APRENDIZAJE ───┐                                       │
│  │  [Historian] [Professor]│  ┌─ CEO OFFICE ──────────────────┐  │
│  └─────────────────────────┘  │  [ALFARO — CEO]               │  │
│                                │  CEO Chat + Trade Approval    │  │
│  SPECIALS: [Eleventh Man] [Maverick]                            │  │
│  META: [Tokin] [Custom Agent Creator]                           │  │
└─────────────────────────────────────────────────────────────────┘
   Port 8790 | PixiJS 8 | React 19 | TypeScript | SQLite | WebSocket
```

**Features de Claw-Empire que usamos:**
- Departamentos con zonas visuales separadas
- Agentes con sprites, animaciones, XP, roles
- CEO Chat con sistema de directivas (`$analyze NVDA`)
- Kanban board: Inbox → Planned → Collaborating → In Progress → Review → Done
- PowerPoint export automático de reportes
- AES-256-GCM para tokens y API keys en SQLite
- WebSocket real-time para updates en vivo
- Sistema de meetings con AI-generated minutes
- Docker deployment listo

**Features que AGREGAMOS:**
- Agente-contrata-agente (spawn autónomo de nuevos agentes)
- Click-to-follow (cámara sigue al agente seleccionado)
- Click-to-talk (chat directo con cualquier agente con un click)
- TradingView Lightweight Charts con overlays de agentes
- Panel de aprobación de trades (prominente, no enterrado)
- Market ticker en vivo (SPY, BTC, EUR/USD, VIX, Gold)
- Carrion aesthetic para momentos de trade (efectos de luz roja, animaciones fluidas)
- Trade report como PDF/PPT con charts incrustados

### Estética Visual

**Terraria (día normal):**
- Pixel art chunky, sprites 2D con bordes de madera/piedra
- Paleta de colores cálida: naranjas, marrones, dorados, tierra
- Atmósfera subterránea de trading floor con antorchas
- UI panels con bordes de bloques estilo RPG
- Agentes sentados en escritorios, caminando entre departamentos
- Speech bubbles para mensajes, animaciones de "pensar"
- Inventario-style para manejo de agentes y estrategias
- Árboles de progresión visibles para XP de agentes

**Carrion (trade encontrado / momento importante):**
- El floor se oscurece, contraste alto rojo/negro
- Pulso de luz roja cuando hay consenso o señal de trade
- Data streams entre agentes se iluminan en rojo/naranja
- Animaciones de agentes se vuelven fluidas, urgentes, orgánicas
- El sistema "se despierta" — se siente VIVO y PODEROSO
- The Boss en la CEO office brilla cuando está decidiendo
- Cuando The Shield veta algo: efecto de alarma visual

### Capa 2: Python Brain (FastAPI)

```
┌─────────────────────────────────────────────────────────────────┐
│  PYTHON TRADING BRAIN                                            │
│                                                                   │
│  FastAPI (REST + WebSocket bridge → puerto 8791)                │
│                                                                   │
│  ┌─ LangGraph Orchestration ──────────────────────────────────┐  │
│  │  25 agentes de trading como nodos del grafo               │  │
│  │  Flujo: Research → Analysis → Strategy → Decision         │  │
│  │  Paralelo dentro de cada departamento                     │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─ Redis Knowledge Bus ──────────────────────────────────────┐  │
│  │  Pub/Sub entre los 25 agentes                             │  │
│  │  Cache: precios 1min TTL, noticias 5min, fundamentales 1h │  │
│  │  Dedup: SHA-256 hash → sin procesar la misma info 2 veces  │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─ ChromaDB ─────────────────────────────────────────────────┐  │
│  │  Memoria semántica: "esta situación la vi en 2023..."     │  │
│  │  Búsqueda vectorial de situaciones históricas similares   │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─ Celery Workers ───────────────────────────────────────────┐  │
│  │  Scheduling dinámico, market-hours aware                  │  │
│  │  DB-driven: nuevos agentes = inclusión automática         │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
   Port 8791 | Python 3.11+ | TradingAgents Framework | LangGraph
```

### Capa 3: OpenClaw (Mensajería — ya corriendo)

```
┌─────────────────────────────────────────────────────────────────┐
│  OPENCLAW GATEWAY (https://openclaw.ai)                          │
│  Self-hosted, local, MIT license                                 │
│                                                                   │
│  ✅ WhatsApp via Baileys (QR-linked, $0/mes)                    │
│  ✅ Telegram, Discord, Slack, Signal, iMessage disponibles      │
│                                                                   │
│  The Messenger es el ÚNICO agente que toca OpenClaw.            │
│  Ningún otro agente envía mensajes directamente.                │
│                                                                   │
│  Formato de aprobación de trade:                                │
│  🔔 NVDA SELL — 78% | Risk 1.5% | R:R 1:3.2                    │
│  [✅ APPROVE] [❌ REJECT] [📄 REPORT] [✏️ MODIFY]              │
│                                                                   │
│  Reminder: 30min sin respuesta                                  │
│  Auto-cancel: 2hr sin respuesta                                 │
│  Digest diario: 9am ET                                          │
└─────────────────────────────────────────────────────────────────┘
   Port 18789 | Node.js 24 | WhatsApp Web / Baileys
```

### Flujo Completo de un Trade

```
1. RECOLECCIÓN (Dept 1, paralelo)
   X-Ray + Headlines + Charts + Scheduler + Cryptid + Globe + Ape + Recon + Accountant
   → todos publican al Redis Knowledge Bus simultáneamente

2. ANÁLISIS (Dept 2, paralelo)
   Mood Ring fusiona sentimientos → score unificado (-100 a +100)
   Pattern Master convierte datos técnicos en setups accionables
   Bull prepara el caso más fuerte para COMPRAR
   Bear prepara el caso más fuerte para NO COMPRAR
   The Bridge identifica correlaciones cross-asset
   → Bull vs Bear debaten 2-5 rondas, todo publicado al bus

3. ESTRATEGIA (Dept 3, secuencial)
   The Architect lee TODO del bus → modera el debate → síntesis
   The Scribe convierte el plan en reporte visual PDF/PPT con TradingView charts
   → The Eleventh Man lee el reporte → añade análisis contrarian obligatorio
   → Maverick añade ideas creativas no convencionales

4. DECISIÓN (Dept 4, secuencial)
   The Shield evalúa riesgo → VETO si viola reglas
   The Boss lee reporte + análisis contrarian → veredicto final
   The Messenger prepara notificación para WhatsApp via OpenClaw

5. APROBACIÓN HUMANA
   Alfaro recibe WhatsApp → [APPROVE] / [REJECT] / [REPORT] / [MODIFY]
   → Si aprueba: The Trigger ejecuta en paper trading
   → Si rechaza: The Professor registra el rechazo y aprende

6. EJECUCIÓN (Dept 5)
   The Trigger ejecuta con stop-loss y take-profit automáticos
   The Watchdog monitorea 24/7 → trailing stops → alertas de cambio

7. APRENDIZAJE (Dept 6)
   The Historian backtestea la estrategia con datos históricos
   The Professor hace post-mortem → ajusta pesos de agentes → actualiza leaderboard
```

---

## INFRAESTRUCTURA DE DATOS

### Tres Capas de Datos

```
┌─ SQLITE (Claw-Empire built-in) ──────────────────────────────────┐
│  departments, agents, tasks, XP, settings, OAuth tokens          │
│  trade_history, agent_performance, strategy_graveyard            │
│  watchlist, api_usage, risk_profiles                             │
│  → Datos estructurados, UI state, historial de trades            │
└──────────────────────────────────────────────────────────────────┘

┌─ CHROMADB (Vector Memory) ───────────────────────────────────────┐
│  Embeddings de todas las situaciones de mercado analizadas       │
│  "Esta setup de NVDA se parece 87% a la de agosto 2023"         │
│  "La última vez que Trump tweeteó esto sobre aranceles..."       │
│  → Memoria semántica a largo plazo del sistema                   │
└──────────────────────────────────────────────────────────────────┘

┌─ REDIS (Real-time Cache + Knowledge Bus) ────────────────────────┐
│  Knowledge Bus pub/sub (mensajes entre agentes en tiempo real)   │
│  Price cache: TTL 1 minuto                                       │
│  News cache: TTL 5 minutos                                       │
│  Fundamentals cache: TTL 1 hora                                  │
│  Deduplication SET: SHA-256 hashes de contenido procesado        │
│  Priority queue: LLM calls cuando múltiples agentes compiten     │
│  → Datos volátiles, comunicación en tiempo real                  │
└──────────────────────────────────────────────────────────────────┘
```

### Schema de SQLite Extendido

**Tablas de Claw-Empire (existentes):**
- `departments` — los 6 departamentos de trading
- `agents` — los 25+ agentes con sprite, XP, stats, role
- `tasks` — análisis de trades en el Kanban
- `workflow_packs` — el pack "trading" que crearemos
- `settings` — configuración del sistema

**Tablas que agregamos:**
- `trades` — historial de todos los trades (paper y real)
- `agent_messages` — log de todos los mensajes del Knowledge Bus
- `agent_performance` — accuracy por agente/mercado/timeframe
- `strategy_graveyard` — estrategias que fallaron + por qué
- `risk_profiles` — perfiles CONSERVATIVE / BALANCED / AGGRESSIVE / CUSTOM
- `api_usage` — llamadas por API vs free tier limits
- `debate_rounds` — transcripción completa de debates Bull vs Bear
- `market_snapshots` — snapshots de mercado en momentos de análisis

---

## SCHEDULING DE AGENTES

### Horario de Mercado (100% capacidad)

**Lunes–Viernes 9:30am–4:00pm ET (Stocks):**
- TODOS los 25 agentes activos al 100%
- Crypto y Forex corriendo en paralelo (24/7)
- Ciclos de análisis completos cada 4 horas
- Ciclos de emergencia on-demand cuando se detecta evento

### Off-Hours — Skeleton Crew (siempre activo)

| Agente | Por qué no puede dormir |
|--------|------------------------|
| X-Ray | Trump puede tweetear a las 2am |
| The Scheduler | Los eventos no esperan |
| Cryptid | Crypto no duerme nunca |
| Globe | Forex corre 24/5, Asia abre cuando USA duerme |
| Tokin | Siempre vigilando el budget |
| The Watchdog | Posiciones abiertas necesitan monitoreo constante |

**Los demás agentes:** duermen off-hours, se activan ON-DEMAND cuando skeleton crew detecta algo importante.

### Escalabilidad del Scheduler

El scheduler **NO tiene los agentes hardcodeados**. Lee la lista de agentes dinámicamente desde la DB. Cuando se agrega un nuevo agente (via Custom Agent Creator), el campo `schedule.frequency` en su config determina automáticamente cuándo corre. Zero cambios de código necesarios.

```python
# Pseudocódigo del scheduler
agents = db.query("SELECT * FROM agents WHERE status != 'offline'")
for agent in agents:
    if is_market_hours() or agent.runs_24_7 or agent.is_skeleton_crew:
        schedule_agent(agent)
    elif event_detected:
        wake_agent(agent)
```

---

## SISTEMA DE RIESGO PERSONALIZABLE

### Perfiles de Riesgo

| Perfil | Max por Trade | Confianza Mínima | Heat Total Máx | Cuándo usar |
|--------|--------------|-----------------|----------------|-------------|
| `CONSERVATIVE` | 1% | >80% | 3% | Mercados volátiles, primera vez |
| `BALANCED` | 2% | >65% | 6% | Default normal |
| `AGGRESSIVE` | 3% | >65% | 9% | Alta confianza, bull market |
| `CUSTOM` | Configurable | Configurable | Configurable | Usuario define todo |

### Multi-Estrategia Simultánea

En paper trading, múltiples perfiles pueden correr al mismo tiempo para comparar resultados:

```
Paper Portfolio A (CONSERVATIVE): $100,000 virtual
Paper Portfolio B (BALANCED): $100,000 virtual
Paper Portfolio C (AGGRESSIVE): $100,000 virtual
→ The Professor compara resultados después de 30 días
→ El mejor perfil tiene más evidencia para recomendar
```

### Reglas Inamovibles de The Shield (VETO automático)

- Risk por trade > límite del perfil activo → VETO
- Heat total del portfolio > límite del perfil → VETO
- Stop-loss > 2× ATR → VETO
- Antes de evento HIGH sin reducción de posición → VETO
- Correlación > 0.8 con posición existente → VETO
- Drawdown del portfolio > 10% → Circuit breaker, pausa TODO

---

## SISTEMA DE GAMIFICACIÓN

### XP de Agentes

Cada agente gana XP por:
- ✅ Trade correcto → +100 XP base × multiplicador de confianza
- ✅ Análisis que el Architect usa → +25 XP
- ✅ Idea de Maverick que se tradea → +200 XP
- ✅ The Eleventh Man previene un trade perdedor → +150 XP
- ❌ Trade incorrecto recomendado → -50 XP
- ❌ False positive / alarma sin fundamento → -25 XP

Niveles de agente: Intern → Junior → Senior → Lead → Expert → Legend

### Leaderboard del Sistema

The Professor mantiene rankings en tiempo real:
- **Por agente:** accuracy total, accuracy por mercado, accuracy por timeframe
- **Por departamento:** el departamento más rentable del mes
- **Por estrategia:** qué tipo de trade genera más P&L
- **Por condición de mercado:** qué configuración funciona mejor en cada régimen (bull/bear/lateral/volátil)

### XP del Usuario (Alfaro)

- Aprobaciones correctas → +XP
- Rechazos correctos (el trade habría perdido) → +XP
- Modificaciones que mejoran el trade → +XP
- Experiencia sube con el tiempo de uso
- Desbloqueos: acceso a estrategias más agresivas, reportes más detallados

### Árbol de Habilidades de Agentes

Cada agente puede "desbloquear" capacidades nuevas a medida que sube de nivel:
- Level 5: acceso a APIs premium adicionales
- Level 10: puede iniciar análisis autónomamente sin esperar el ciclo
- Level 15: puede contratar agentes junior propios
- Level 20: "Legend" — su peso en el consenso es 2×

---

## AGENTE-CONTRATA-AGENTE

Los agentes con suficiente nivel pueden proponer y contratar nuevos agentes especializados:

```
Ejemplo:
The Architect (Level 15) detecta que necesita más análisis de semiconductores.
→ Propone al CEO: "Quiero contratar un especialista en chips"
→ Alfaro aprueba en CEO Chat
→ The Architect usa Custom Agent Creator para definir el nuevo agente
→ El nuevo agente se siembra en la DB automáticamente
→ Aparece en el pixel office con animación de "reclutamiento"
→ The Architect lo asigna a su departamento como junior
```

**Reglas:**
- Solo agentes Level 15+ pueden contratar
- Alfaro SIEMPRE aprueba antes de que el nuevo agente sea creado
- Tokin revisa el costo estimado del nuevo agente antes de aprobar
- El agente que contrata es "mentor" — su XP está ligado al éxito del contratado

---

## CLICK-TO-FOLLOW / CLICK-TO-TALK

### Click-to-Follow
- Click en cualquier agente en el pixel office
- La cámara hace zoom y sigue al agente
- Panel lateral muestra:
  - Qué está haciendo en tiempo real
  - Últimos 10 mensajes publicados al Knowledge Bus
  - Su performance actual (XP, accuracy, último trade analizado)
  - Gráfica de accuracy en el tiempo

### Click-to-Talk
- Double-click en cualquier agente → abre chat directo
- Puedes preguntarle directamente sobre su análisis
- El agente responde en-character con toda la info que tiene en ese momento
- Ejemplos:
  - "X-Ray, ¿por qué marcaste el tweet de Trump como HIGH priority?"
  - "Bull, ¿cuál es tu argumento más fuerte para NVDA?"
  - "The Shield, ¿por qué vetaste ese trade?"
  - "The Professor, ¿quién es el agente más preciso este mes?"

### CEO Chat Broadcast
- Desde el CEO Office puedes escribir a TODOS los agentes simultáneamente
- `$analyze NVDA` → inicia pipeline completo de análisis
- `$status` → todos los agentes reportan su estado actual
- `$pause` → pausa todos los ciclos (modo mantenimiento)
- `$report` → The Scribe genera reporte del estado del portfolio

---

## TRADINGVIEW NATIVE INTEGRATION

TradingView Lightweight Charts se integra directamente (no como widget externo):

```
┌─ TRADINGVIEW CHART (NVDA 1H) ─────────────────────────────────┐
│                                                                  │
│  Precio ────────────────────────────────────────────────────── │
│                    ▲ Entry: $145.00 (Charts + Pattern Master)  │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ (TP2)     │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ (TP1)                          │
│                                                                  │
│  [Charts] señala: Golden cross en 1H                           │
│  [Pattern Master] señala: Bull flag completado                 │
│  [Mood Ring] señala: Sentimiento 72 (bullish)                  │
│  [Maverick] señala: Idea — "Catalysts de earnings en 3 días"  │
│                                                                  │
│  ▼ Stop Loss: $141.00 (The Shield — 1.5% risk)                │
└──────────────────────────────────────────────────────────────────┘
```

**Overlays de agentes en charts:**
- Marcadores de entry/exit/stop por agente
- Líneas de soporte/resistencia de Pattern Master y Charts
- Indicadores técnicos seleccionables (RSI, MACD, Bollinger, etc.)
- Eventos del Scheduler marcados en el timeline (FOMC, earnings, etc.)
- Tweets relevantes de X-Ray anclados en el momento que ocurrieron

**Charts en reportes:**
- The Scribe incrusta charts estáticos en PDFs y PPTs
- Cada reporte tiene el chart con todos los overlays del momento del análisis
- Los reportes muestran el chart de la decisión, no el chart de hoy

---

## TECH STACK COMPLETO

### UI Layer — Claw-Empire (ya existe, lo extendemos)

```
TypeScript 5.9 + React 19 + Vite 7 + Tailwind CSS 4
PixiJS 8                    → pixel art rendering
Express 5 (Node.js)         → backend de UI
SQLite (embedded)           → datos de UI, agentes, tareas, XP
WebSocket (ws)              → updates en tiempo real
PptxGenJS                   → PowerPoint export
React Router 7              → navegación
```

### Python Brain (lo construimos)

```
Python 3.11+
TradingAgents framework     → github.com/TauricResearch/TradingAgents
LangGraph                   → orquestación de agentes
FastAPI                     → REST API + WebSocket bridge
Redis                       → Knowledge Bus + cache
ChromaDB                    → memoria semántica vectorial
Celery + Redis              → scheduling de agentes
SQLite (extendido)          → trades, performance, graveyard
```

### Mensajería (ya corriendo)

```
OpenClaw                    → https://openclaw.ai (self-hosted, local)
WhatsApp via Baileys        → QR-linked, $0/mes
Puerto 18789
```

### AI / LLM

```
Claude API (Anthropic)      → análisis profundo primario
OpenAI GPT                  → validación secundaria
FinBERT (local)             → NLP de sentimiento financiero (gratis)
Ollama (local)              → modelos rápidos para tareas de alta frecuencia
```

### Charts

```
TradingView Lightweight Charts → charts nativos con overlays
PptxGenJS                      → charts en reportes PPT
PDF custom generation          → reportes PDF
```

### APIs de Datos (todas free tier)

```
Alpaca                      → stocks + crypto + paper trading execution
Alpha Vantage               → fundamentales + forex (25 req/día)
CoinGecko                   → crypto (30 req/min)
Finnhub                     → noticias + sentimiento + calendario (60/min)
Financial Modeling Prep     → estados financieros (250 req/día)
Twitter/X API v2            → tweets (10K tweets/mes)
Reddit API / PRAW           → sentimiento de comunidad (gratis)
NewsAPI.ai                  → noticias (200 req/día)
Yahoo Finance / yfinance    → datos históricos (gratis, ilimitado)
FRED API                    → datos económicos USA (gratis)
DeFi Llama                  → datos DeFi (gratis)
GDELT Project               → eventos geopolíticos (gratis)
FXCM                        → forex demo (gratis)
OANDA                       → forex practice (gratis)
Etherscan                   → on-chain ETH (gratis)
Alternative.me              → Fear & Greed Index (gratis)
```

### Seguridad

```
1Password CLI               → injecta secrets como env vars en Docker startup
.env file                   → fallback local (siempre gitignoreado)
Claw-Empire AES-256-GCM    → OAuth tokens + messenger tokens en SQLite
LIVE_TRADING=false flag     → previene ejecución real accidentalmente
```

### Infraestructura

```
Docker Compose              → un solo comando levanta todo
  Services: claw-empire, python-brain, redis, chromadb, celery
  Modo interactivo: docker compose up
  Modo 24/7: docker compose up -d (restart: unless-stopped)
  Datos en: ./data/ (persiste entre reinicios)
  PC local por ahora → VPS después cuando esté probado
```

### Estimado de Costos

| Componente | Costo/mes |
|-----------|-----------|
| Infraestructura + APIs (free tiers) | $0 |
| OpenClaw (self-hosted) | $0 |
| Claude API (análisis LLM) | ~$10–30 |
| **Total operacional** | **~$10–30** |
| Máximo con upgrades premium | ~$65–100 |

---

## DEPLOYMENT

### Modo On-Demand (cuando quieres usarlo)
```bash
docker compose up
# Ctrl+C para detener
```

### Modo 24/7 (background, reinicia solo)
```bash
docker compose up -d
docker compose down  # para detener
```

### docker-compose.yml (estructura)
```yaml
services:
  claw-empire:       # UI en puerto 8790
  python-brain:      # FastAPI en puerto 8791
  redis:             # Knowledge Bus + cache
  chromadb:          # Memoria semántica
  celery-worker:     # Scheduling de agentes
  celery-beat:       # Cron de scheduling

volumes:
  ./data:/app/data   # todos los datos persisten aquí
```

---

## ROADMAP DE IMPLEMENTACIÓN (4 SEMANAS)

### SEMANA 1 — Fundaciones

```
□ Clonar Claw-Empire en /home/luisalfaro/Desktop/Coding/TradingAICenter/
□ Renombrar los 6 departamentos a los de trading
□ Sembrar los 25 agentes en la DB con sus configs
□ Crear el Workflow Pack "trading"
□ Aplicar paleta Terraria (colores, temas de room)
□ docker compose up — primer instancia local funcional
□ CEO Chat respondiendo comandos básicos
```

### SEMANA 2 — Python Brain

```
□ FastAPI setup + bridge WebSocket a Claw-Empire
□ Redis Knowledge Bus funcionando
□ ChromaDB inicializado
□ Celery workers con market-hours awareness
□ Primeros 3 agentes reales: Charts, X-Ray, The Scheduler
□ Knowledge Bus mandando mensajes reales entre agentes
□ Datos de Alpaca llegando en tiempo real
```

### SEMANA 3 — Pipeline Completo

```
□ Los 9 agentes de Investigación activos
□ Bull + Bear debatiendo en tiempo real
□ The Architect sintetizando planes de trade
□ The Scribe generando PDFs/PPTs con charts
□ The Shield evaluando riesgo
□ The Boss dando veredictos
□ The Messenger enviando via OpenClaw/WhatsApp
□ Trade approval flow funcional end-to-end
□ Alpaca paper trading ejecutando trades aprobados
```

### SEMANA 4 — Demo Quality

```
□ Todos los 25 agentes desplegados
□ Carrion aesthetic para momentos de trade
□ TradingView charts con overlays de agentes
□ Click-to-follow y click-to-talk funcional
□ Gamificación: XP, leaderboard, árbol de habilidades
□ CEO Chat broadcast a todos los agentes
□ The Professor tracking accuracy en tiempo real
□ Paper trading activo con múltiples perfiles de riesgo
□ 30 días mínimos de paper trading antes de discutir dinero real
```

---

## LOS 25 AGENTES — REFERENCIA RÁPIDA

### Dept 1: Investigación (Research Floor)

| ID | Nombre | Role | Mercados | APIs Principales | Corre |
|----|--------|------|----------|-----------------|-------|
| 1.1 | X-Ray | Twitter/X + Política | ALL | Twitter API, GDELT, StockGeist | 24/7 |
| 1.2 | The Scheduler | Calendario económico | ALL | Finnhub, Alpha Vantage | 24/7 |
| 1.3 | Headlines | Noticias financieras | ALL | Finnhub, NewsAPI.ai, RSS | Market hours |
| 1.4 | Charts | Datos técnicos OHLCV | ALL | Alpaca, yfinance, TA-Lib | Market hours |
| 1.5 | The Accountant | Fundamentales | Stocks | FMP, SEC EDGAR, Alpha Vantage | Market hours |
| 1.6 | Cryptid | Crypto + on-chain | Crypto | CoinGecko, Etherscan, DeFi Llama | 24/7 |
| 1.7 | Globe | Forex + macro | Forex | FRED, Alpha Vantage Forex, OANDA | 24/7 |
| 1.8 | Ape | Reddit + comunidad | ALL | Reddit PRAW, StockTwits | Market hours |
| 1.9 | Recon | Datos alternativos | ALL | Finnhub, FMP, SEC EDGAR | Market hours |

### Dept 2: Análisis (Analysis Floor)

| ID | Nombre | Role | Input | Output |
|----|--------|------|-------|--------|
| 2.1 | Mood Ring | Fusión de sentimiento | Todo Dept 1 | Score -100 a +100 |
| 2.2 | Pattern Master | Análisis técnico | Charts | Setups accionables (1-5 ⭐) |
| 2.3 | Bull | Investigador bullish | Todo el bus | Caso de COMPRA más fuerte |
| 2.4 | Bear | Investigador bearish | Todo el bus | Caso de VENTA/NO COMPRA más fuerte |
| 2.5 | The Bridge | Correlaciones cross-asset | Todo el bus | Divergencias y correlaciones |

### Dept 3: Estrategia (Strategy Room)

| ID | Nombre | Role | Input | Output |
|----|--------|------|-------|--------|
| 3.1 | The Architect | Síntesis + plan de trade | Debate Bull/Bear | Plan coherente de trade |
| 3.2 | The Scribe | Generador de reportes | Plan del Architect | PDF/PPT con charts y tablas |

### Dept 4: Decisión y Riesgo (Executive Suite)

| ID | Nombre | Role | Poderes |
|----|--------|------|---------|
| 4.1 | The Shield | Risk Manager | **VETO POWER** — puede bloquear cualquier trade |
| 4.2 | The Boss | Decision Chief | Veredicto final (STRONG BUY/BUY/HOLD/SKIP/SELL) |
| 4.3 | The Messenger | Human Interface | Único que toca WhatsApp via OpenClaw |

### Dept 5: Ejecución (Trading Desk)

| ID | Nombre | Role | Brokers |
|----|--------|------|---------|
| 5.1 | The Trigger | Trade executor | Alpaca (stocks/crypto), FXCM, OANDA |
| 5.2 | The Watchdog | Position monitor | Alpaca, FXCM, OANDA — 24/7 |

### Dept 6: Aprendizaje (Research Lab)

| ID | Nombre | Role | Frameworks |
|----|--------|------|-----------|
| 6.1 | The Historian | Backtester | Backtesting.py, VectorBT, NautilusTrader |
| 6.2 | The Professor | Learning engine | SQLite + ChromaDB, Agent Leaderboard |

### Agentes Especiales

| ID | Nombre | Role | Regla sagrada |
|----|--------|------|--------------|
| S.1 | The Eleventh Man | Contrarian obligatorio | SIEMPRE toma la posición opuesta al consenso |
| S.2 | Maverick | Estratega creativo | Genera ideas que nadie más generaría |

### Meta-Sistema

| Componente | Función |
|-----------|---------|
| Tokin | CFO del sistema — veta LLM calls si se acaba el budget |
| Custom Agent Creator | Crea agentes nuevos via lenguaje natural |

---

## ESTADO DEL PROYECTO (2026-04-13)

### Infraestructura

| Componente | Estado | Notas |
|-----------|--------|-------|
| OpenClaw | ✅ Corriendo | WhatsApp gateway local, puerto 18789 |
| CLAUDE.md | ✅ Actualizado | Toda la documentación al día |
| BLUEPRINT v3 | ✅ Este documento | |
| Claw-Empire | 🔲 Pendiente | Semana 1 — clonar y adaptar |
| Python Brain | 🔲 Pendiente | Semana 2 |
| Redis | 🔲 Pendiente | Parte del docker-compose |
| ChromaDB | 🔲 Pendiente | Parte del docker-compose |
| Paper Trading | 🔲 Pendiente | Semana 3–4 |

### Decisiones Abiertas

| Área | Estado |
|------|--------|
| Diseño visual (colores exactos, sprites) | 🟡 Decidido en concepto, implementar en Semana 1 |
| Workflow Pack "trading" (schema exacto) | 🟡 Estructura conocida, definir en Semana 1 |
| VPS / servidor externo | 🔲 Después de paper trading exitoso |
| Estrategia de live trading | 🔲 Mínimo 30 días paper trading primero |

---

## ARCHIVOS DEL PROYECTO

| Archivo | Descripción | Estado |
|---------|-------------|--------|
| `CLAUDE.md` | Contexto completo del proyecto para AI | ✅ Actualizado |
| `Documentacion/BLUEPRINT_AgentTeams_v1.md` | Blueprint original (archivado) | 📁 Referencia |
| `Documentacion/BLUEPRINT_AgentTeams_v2.md` | Blueprint con Knowledge Bus y prompts (archivado) | 📁 Referencia |
| `Documentacion/BLUEPRINT_AgentTeams_v3.md` | Este documento — versión actual | ✅ Actual |
| `Documentacion/UI_COMPARISON_Guide.md` | Comparación de 3 opciones de UI — decisión tomada | ✅ Archivado |
| `Documentacion/PLAN_MAESTRO_TradingAICenter.md` | Plan maestro original | 📁 Referencia |

---

> **Nota para el próximo AI que lea esto:**
> El proyecto está en fase de planificación completa. Toda decisión está tomada.
> El siguiente paso de código es la Semana 1: clonar Claw-Empire, adaptar departamentos, sembrar agentes.
> OpenClaw ya está corriendo en puerto 18789. La UI base es Claw-Empire.
> El backend de trading será Python FastAPI en puerto 8791.
> Estética: Terraria para UI normal, Carrion para momentos de trade.
> El humano es Alfaro — siempre requiere aprobación antes de ejecutar cualquier trade.
