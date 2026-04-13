# TradingAICenter - Plan Maestro de Arquitectura

## Vision General

Un centro de análisis multi-mercado (Stocks, Crypto, Forex) con múltiples agentes de IA especializados que se comunican entre sí, investigan información en tiempo real, y generan recomendaciones de trading con aprobación humana antes de ejecutar. La UI será un sistema visual estilo "pixel agents" donde puedes ver el flujo completo de pensamiento, comunicación e investigación entre agentes.

---

## 1. ARQUITECTURA DE AGENTES

### Capa 1: Agentes Investigadores (Data Gatherers)

| Agente | Función | Fuente de Datos | API/Herramienta |
|--------|---------|-----------------|-----------------|
| **Twitter/X Trend Scout** | Monitorea tendencias, sentimiento, menciones de tickers | Twitter/X | Twitter API v2 (Free tier: 10K tweets/mes) o snscrape (gratis) |
| **Economic Calendar Watcher** | Calendario económico, NFP, CPI, FOMC, etc. | Forex Factory, Investing.com | Alpha Vantage API (gratis) + web scraping |
| **News Analyst** | Noticias financieras en tiempo real | Reuters, Bloomberg, Yahoo Finance | Yahoo Finance API (gratis) + NewsAPI ($0 - 100 req/día gratis) |
| **Technical Analyst** | Análisis técnico: RSI, MACD, Bollinger, soportes/resistencias | Datos de mercado en vivo | TradingView (widgets gratis) + TA-Lib (open source) |
| **Fundamental Analyst** | Earnings, P/E, revenue, balance sheets | SEC filings, financial statements | Alpha Vantage + Financial Modeling Prep API (250 req/día gratis) |
| **Crypto Scanner** | Precios, volumen, whale movements, DeFi metrics | Blockchain data | CoinGecko API (gratis) + Etherscan API (gratis) |
| **Forex Monitor** | Pares de divisas, correlaciones, carry trade data | Forex market data | Alpha Vantage Forex + OANDA API (gratis para datos) |
| **Reddit Sentiment Agent** | Sentimiento en r/wallstreetbets, r/stocks, r/crypto | Reddit | Reddit API (gratis con OAuth) |

### Capa 2: Agentes Analistas (Processors)

| Agente | Función | Recibe Info De |
|--------|---------|----------------|
| **Sentiment Aggregator** | Combina sentimiento de Twitter, Reddit, News | Twitter Scout, Reddit Agent, News Analyst |
| **Market Correlator** | Encuentra correlaciones entre mercados | Todos los investigadores |
| **Risk Assessor** | Evalúa riesgo/reward de cada oportunidad | Technical Analyst, Fundamental Analyst |
| **Pattern Recognizer** | Detecta patrones históricos similares | Technical Analyst, Market Correlator |

### Capa 3: Agente Estratega (The Planner)

| Agente | Función |
|--------|---------|
| **Strategy Planner** | Recibe TODA la información procesada. Sintetiza en un plan de trading coherente. Identifica las mejores oportunidades. Asigna prioridades y niveles de confianza. |

### Capa 4: Agente Documentador (Report Generator)

| Agente | Función |
|--------|---------|
| **Report Writer** | Crea documentos completos con: análisis detallado, gráficos, justificación de cada trade propuesto, niveles de entrada/salida/stop-loss, y nivel de confianza. |

### Capa 5: Agente Jefe de Decisiones (The Boss)

| Agente | Función |
|--------|---------|
| **Decision Chief** | Revisa el reporte final. Evalúa si es buena idea o no. Da veredicto final: BUY / SELL / HOLD / SKIP. Explica su razonamiento. Envía notificación al humano para aprobación. |

### Capa 6: Agente Ejecutor (con aprobación humana)

| Agente | Función |
|--------|---------|
| **Trade Executor** | Solo actúa después de aprobación humana. Ejecuta trades vía Alpaca API. Monitorea posiciones abiertas. Gestiona stop-loss y take-profit. |

---

## 2. COMUNICACIÓN ENTRE AGENTES

### Framework Recomendado: LangGraph + Custom Message Bus

```
Opción A: TradingAgents Framework (Open Source)
- Ya implementa exactamente esta arquitectura multi-agente
- Usa LangGraph para orquestación
- Soporta múltiples LLMs (Claude, GPT, Gemini, Grok)
- GitHub: TauricResearch/TradingAgents
- GRATIS

Opción B: CrewAI
- Framework popular para multi-agentes
- Fácil de definir roles y tareas
- Soporta comunicación entre agentes
- GRATIS (open source)

Opción C: AutoGen (Microsoft)
- Multi-agent conversation framework
- Excelente para debates entre agentes
- GRATIS

RECOMENDACIÓN: Usar TradingAgents como base y extenderlo
con agentes custom usando LangGraph.
```

### Protocolo de Comunicación

```
[Investigadores] → Message Queue → [Analistas]
[Analistas] → Structured Report → [Strategy Planner]
[Strategy Planner] → Trade Plan → [Report Writer]
[Report Writer] → Full Document → [Decision Chief]
[Decision Chief] → Verdict + Alert → [Human Dashboard]
[Human Approval] → Execute Signal → [Trade Executor]
```

Cada mensaje entre agentes incluye:
- Timestamp
- Agent ID (remitente)
- Agent ID (destinatario)
- Tipo de mensaje (data_update, analysis, recommendation, alert)
- Payload (la información)
- Confidence Score (0-100)
- Priority (low, medium, high, critical)

---

## 3. UI VISUAL - "MINI WALL STREET"

### Concepto: Pixel Agent Trading Floor

Basado en el proyecto open-source **Pixel Agents** (GitHub: pablodelucca/pixel-agents), adaptado para trading:

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRADINGAI CENTER - TRADING FLOOR              │
├──────────────────────────┬──────────────────────────────────────┤
│                          │                                      │
│   🏢 PIXEL OFFICE        │   📊 LIVE DASHBOARD                  │
│                          │                                      │
│   [Twitter Scout]        │   ┌──────────┐ ┌──────────┐         │
│   💬 "Encontré trend     │   │ S&P 500  │ │ BTC/USD  │         │
│    de $NVDA..."          │   │ ▲ 5,234  │ │ ▲ 98,432 │         │
│                          │   └──────────┘ └──────────┘         │
│   [Econ Calendar] →      │                                      │
│   📨 enviando a          │   ┌──────────┐ ┌──────────┐         │
│    Strategy Planner      │   │ EUR/USD  │ │ FEAR IDX │         │
│                          │   │ ▼ 1.0834 │ │ 😰 32    │         │
│   [Strategy Planner]     │   └──────────┘ └──────────┘         │
│   🤔 pensando...         │                                      │
│                          │   ┌─────────────────────────┐       │
│   [Decision Chief]       │   │ AGENT ACTIVITY LOG      │       │
│   ⏳ esperando reporte   │   │ 10:32 - Twitter found   │       │
│                          │   │ 10:33 - Analyzing...    │       │
│   [Trade Executor]       │   │ 10:35 - Report ready    │       │
│   💤 idle                │   │ 10:36 - ALERT: Buy NVDA │       │
│                          │   └─────────────────────────┘       │
├──────────────────────────┴──────────────────────────────────────┤
│ 📋 LATEST REPORT: NVDA Analysis | Confidence: 87% | AWAITING   │
│ YOUR APPROVAL  [✅ APPROVE] [❌ REJECT] [📄 VIEW FULL REPORT]   │
└─────────────────────────────────────────────────────────────────┘
```

### Tecnología para la UI

```
Opción A (Recomendada): React + Pixel Agents adaptado
- Framework: React / Next.js
- Pixel Art: PixiJS o Phaser para sprites animados
- Dashboard: Recharts + TradingView Lightweight Charts (gratis)
- WebSocket para actualizaciones en tiempo real
- Costo: GRATIS

Opción B: Electron App
- App de escritorio dedicada
- Basada en pixel-agent-desk (Electron)
- Más control sobre el sistema
- Costo: GRATIS

Opción C: Streamlit + Custom Components
- Más rápido de prototipar
- Menos visual pero funcional
- Costo: GRATIS
```

---

## 4. HERRAMIENTAS DE AI TRADING EXISTENTES PARA INTEGRAR

### Tier 1: Integrables vía API (Recomendados)

| Herramienta | Integración | Costo | Para Qué |
|-------------|------------|-------|----------|
| **Alpaca** | API REST + MCP Server oficial | GRATIS (paper trading) | Ejecución de trades, datos de mercado |
| **Alpha Vantage** | API REST + MCP support | GRATIS (25 req/día) o $49.99/mes | Datos fundamentales, técnicos, forex |
| **TradingAgents** | Framework open source | GRATIS | Base del sistema multi-agente |
| **CoinGecko** | API REST | GRATIS (30 req/min) | Datos crypto |
| **Yahoo Finance** | yfinance (Python) | GRATIS | Datos de acciones históricos |
| **TradingView** | Widgets embebidos + Lightweight Charts | GRATIS | Gráficos interactivos en la UI |

### Tier 2: Herramientas Externas con API Limitada

| Herramienta | Integración | Costo | Para Qué |
|-------------|------------|-------|----------|
| **Trade Ideas (Holly AI)** | No tiene API pública, pero tiene alertas exportables | ~$118/mes | Escaneo de mercado con AI |
| **TrendSpider** | API limitada, webhooks disponibles | ~$33-97/mes | Análisis técnico automatizado |
| **Tickeron** | API para AI Robots alerts | ~$50/mes | Señales de trading AI |

### Tier 3: Open Source para construir internamente

| Herramienta | Uso | Costo |
|-------------|-----|-------|
| **TA-Lib** | Indicadores técnicos | GRATIS |
| **FinBERT** | Sentiment analysis de texto financiero | GRATIS |
| **Whisper (OpenAI)** | Transcribir earnings calls | GRATIS |
| **LangChain/LangGraph** | Orquestación de agentes | GRATIS |

---

## 5. STACK TECNOLÓGICO PROPUESTO

```
Backend:
├── Python 3.11+
├── LangGraph (orquestación de agentes)
├── TradingAgents framework (base)
├── FastAPI (API del sistema)
├── Redis (message queue entre agentes)
├── SQLite/PostgreSQL (almacenamiento de datos y reportes)
└── Celery (tareas asíncronas y scheduling)

Frontend:
├── React / Next.js
├── PixiJS (pixel art sprites animados)
├── TradingView Lightweight Charts
├── Recharts (gráficos adicionales)
├── WebSocket (actualizaciones en tiempo real)
└── Tailwind CSS (estilos)

AI/LLM:
├── Claude API (análisis principal) - ya incluido en tu suscripción
├── OpenAI GPT (agente alternativo/validación cruzada)
├── FinBERT (sentiment analysis especializado)
└── TradingAgents multi-LLM support

APIs de Datos:
├── Alpaca (stocks + ejecución)
├── Alpha Vantage (datos fundamentales + forex)
├── CoinGecko (crypto)
├── Twitter/X API (sentimiento social)
├── Reddit API (sentimiento comunidad)
├── NewsAPI (noticias)
└── Yahoo Finance (datos históricos)
```

---

## 6. ESTIMACIÓN DE COSTOS MENSUALES

| Servicio | Tier | Costo/mes |
|----------|------|-----------|
| Alpaca (paper trading) | Free | $0 |
| Alpha Vantage | Free (25 req/día) | $0 |
| CoinGecko API | Free | $0 |
| Twitter/X API | Free (básico) | $0 |
| Reddit API | Free | $0 |
| NewsAPI | Free (100 req/día) | $0 |
| Yahoo Finance (yfinance) | Free | $0 |
| Claude API | Pay per use | ~$10-30 |
| TradingView Charts | Free (lightweight) | $0 |
| Hosting (si se despliega) | VPS básico | $5-20 |
| **TOTAL ESTIMADO** | | **$15-50/mes** |

Si quieres datos en tiempo real premium: Alpha Vantage Premium = $49.99/mes → Total ~$65-100/mes

---

## 7. FASES DE IMPLEMENTACIÓN

### Fase 1: Fundación (Semana 1-2)
- [ ] Configurar proyecto base (Python + React)
- [ ] Implementar TradingAgents framework
- [ ] Configurar APIs gratuitas (Alpha Vantage, CoinGecko, Yahoo Finance)
- [ ] Crear sistema básico de mensajería entre agentes (Redis)
- [ ] Primer agente funcional: Technical Analyst

### Fase 2: Agentes Investigadores (Semana 3-4)
- [ ] Twitter/X Trend Scout
- [ ] Economic Calendar Watcher
- [ ] News Analyst
- [ ] Crypto Scanner
- [ ] Reddit Sentiment Agent
- [ ] Forex Monitor

### Fase 3: Agentes de Procesamiento (Semana 5-6)
- [ ] Sentiment Aggregator
- [ ] Market Correlator
- [ ] Risk Assessor
- [ ] Strategy Planner
- [ ] Report Writer
- [ ] Decision Chief

### Fase 4: UI Visual - Pixel Trading Floor (Semana 7-8)
- [ ] Setup React + PixiJS
- [ ] Crear sprites para cada agente
- [ ] Animaciones de estados (pensando, enviando, idle)
- [ ] Dashboard con gráficos en tiempo real
- [ ] Activity log y message visualization
- [ ] Panel de aprobación humana

### Fase 5: Ejecución y Alpaca (Semana 9-10)
- [ ] Integrar Alpaca MCP Server
- [ ] Trade Executor con aprobación humana
- [ ] Paper trading testing completo
- [ ] Alertas y notificaciones

### Fase 6: Refinamiento (Semana 11-12)
- [ ] Backtesting con datos históricos
- [ ] Optimización de prompts de cada agente
- [ ] Performance monitoring
- [ ] Documentación completa

---

## 8. DIAGRAMA DE FLUJO COMPLETO

```
                    ┌─────────────────┐
                    │   DATA SOURCES   │
                    │ Twitter, News,   │
                    │ Reddit, Calendars│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  INVESTIGADORES  │
                    │ (8 agentes)      │
                    │ Cada uno en su   │
                    │ especialidad     │
                    └────────┬────────┘
                             │ raw data + initial analysis
                    ┌────────▼────────┐
                    │   ANALISTAS      │
                    │ (4 agentes)      │
                    │ Sentiment, Risk, │
                    │ Correlations     │
                    └────────┬────────┘
                             │ processed insights
                    ┌────────▼────────┐
                    │ STRATEGY PLANNER │
                    │ (1 agente)       │
                    │ Sintetiza todo   │
                    └────────┬────────┘
                             │ trade plan
                    ┌────────▼────────┐
                    │  REPORT WRITER   │
                    │ (1 agente)       │
                    │ Documento formal │
                    └────────┬────────┘
                             │ full report
                    ┌────────▼────────┐
                    │ DECISION CHIEF   │
                    │ (1 agente)       │
                    │ Veredicto final  │
                    └────────┬────────┘
                             │ BUY/SELL/HOLD + explanation
                    ┌────────▼────────┐
                    │  🧑 HUMANO (TÚ)  │
                    │ Aprueba/Rechaza  │
                    └────────┬────────┘
                             │ approved
                    ┌────────▼────────┐
                    │ TRADE EXECUTOR   │
                    │ (Alpaca API)     │
                    │ Ejecuta trade    │
                    └─────────────────┘
```

---

## 9. REPOS Y RECURSOS CLAVE

- **TradingAgents Framework**: https://github.com/TauricResearch/TradingAgents
- **Pixel Agents (UI inspiration)**: https://github.com/pablodelucca/pixel-agents
- **Pixel Agent Desk (Electron)**: https://github.com/Mgpixelart/pixel-agent-desk
- **Alpaca MCP Server**: https://github.com/alpacahq/alpaca-mcp-server
- **Alpaca API Docs**: https://docs.alpaca.markets/
- **Alpha Vantage API**: https://www.alphavantage.co/documentation/
- **TradingView Lightweight Charts**: https://github.com/nicfru/lightweight-charts
- **LangGraph**: https://github.com/langchain-ai/langgraph
- **FinBERT**: https://github.com/ProsusAI/finBERT
- **TA-Lib**: https://github.com/TA-Lib/ta-lib-python
