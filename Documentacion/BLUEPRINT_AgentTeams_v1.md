# TradingAICenter - Blueprint Detallado de Equipos de Agentes v1

## Base: TradingAgents Framework + Agent Office Visualization

### Arquitectura Original de TradingAgents (lo que ya tiene):

```
4 Analistas → 2 Researchers (Bull vs Bear debate) → Trader → Risk Manager → Fund Manager
```

### Nuestra Arquitectura Extendida (lo que vamos a construir):

```
DEPARTAMENTO 1: INVESTIGACIÓN (9 agentes)
         ↓ raw intelligence
DEPARTAMENTO 2: ANÁLISIS (5 agentes)
         ↓ processed insights + bull/bear debate
DEPARTAMENTO 3: ESTRATEGIA (2 agentes)
         ↓ trade plans + full reports
DEPARTAMENTO 4: DECISIÓN Y RIESGO (3 agentes)
         ↓ approved/rejected signals
DEPARTAMENTO 5: EJECUCIÓN (2 agentes)
         ↓ paper trades executed
DEPARTAMENTO 6: APRENDIZAJE (2 agentes)
         ↓ feedback loop → mejora continua
```

---

## DEPARTAMENTO 1: INVESTIGACIÓN (Research Floor)

> **Misión:** Recopilar TODA la información cruda del mercado en tiempo real. Cada agente es un especialista que sabe exactamente dónde buscar y qué extraer.

---

### 🔵 Agente 1.1: Twitter/X Sentiment Scout

**Nombre en pixel office:** "X-Ray"
**Personalidad:** Rápido, impulsivo, siempre atento. El que llega corriendo con noticias de última hora.

**¿Qué investiga?**
- Trending tickers ($AAPL, $BTC, etc.)
- Sentimiento general sobre acciones/crypto específicas
- Tweets de influencers financieros (Elon Musk, Cathie Wood, etc.)
- Cambios repentinos en volumen de menciones (spike detection)
- Hashtags financieros trending (#stockmarket, #crypto, #forex)
- Alertas de insider trading reveladas en social media

**¿De dónde saca la info?**

| Fuente | API/Método | Costo | Datos |
|--------|-----------|-------|-------|
| Twitter/X API v2 | REST API + Streaming | Free (Basic): 10K tweets/mes, $100/mes (Pro): 1M tweets/mes | Tweets, likes, retweets, mentions |
| StockGeist API | REST API | Free tier disponible | Sentiment scores pre-calculados por ticker |
| snscrape (backup) | Python scraper | Gratis | Tweets históricos sin límite de API |

**Output que genera:**
```json
{
  "agent": "twitter_scout",
  "timestamp": "2026-03-18T10:32:00Z",
  "ticker_mentions": {
    "$NVDA": {"count": 4523, "sentiment": 0.78, "spike": true, "delta_1h": "+340%"},
    "$TSLA": {"count": 2100, "sentiment": 0.45, "spike": false, "delta_1h": "+12%"}
  },
  "influencer_alerts": [
    {"user": "@elonmusk", "tweet": "...", "tickers_mentioned": ["$TSLA"], "impact_score": 95}
  ],
  "trending_hashtags": ["#AIStocks", "#NVDAEarnings"],
  "overall_market_mood": "bullish",
  "confidence": 72
}
```

---

### 🟢 Agente 1.2: Economic Calendar Watcher

**Nombre en pixel office:** "The Scheduler"
**Personalidad:** Metódico, puntual, obsesionado con fechas. Tiene un reloj gigante en su escritorio.

**¿Qué investiga?**
- Próximos eventos económicos (NFP, CPI, FOMC, GDP, Unemployment)
- Decisiones de tasas de interés de bancos centrales (Fed, ECB, BoJ, BoE)
- Earnings reports programados (cuándo reporta cada empresa)
- IPOs y splits programados
- Ex-dividend dates
- Vencimientos de opciones (OpEx)
- Datos macroeconómicos por país (15+ países)
- Impacto histórico de cada tipo de evento

**¿De dónde saca la info?**

| Fuente | API/Método | Costo | Datos |
|--------|-----------|-------|-------|
| Finnhub Economic Calendar | REST API | Free: 60 calls/min | Calendario económico global |
| Alpha Vantage | REST API | Free: 25 req/día, Premium: $49.99/mes | Earnings calendar, economic indicators |
| Forex News API | REST API | Free tier | 800+ eventos, 15 países, con sentiment |
| EODHD Calendar API | REST API | Free tier: limitado | Economic calendar + IPOs + earnings |
| Investing.com | Web scraping (backup) | Gratis | Calendario completo |

**Output que genera:**
```json
{
  "agent": "economic_calendar",
  "timestamp": "2026-03-18T06:00:00Z",
  "upcoming_events_24h": [
    {
      "event": "FOMC Interest Rate Decision",
      "datetime": "2026-03-18T18:00:00Z",
      "country": "US",
      "impact": "HIGH",
      "previous": "4.50%",
      "forecast": "4.25%",
      "historical_market_reaction": {
        "avg_sp500_move": "±1.2%",
        "avg_btc_move": "±3.5%",
        "direction_if_cut": "bullish 78% of time"
      }
    }
  ],
  "earnings_today": [
    {"company": "NVDA", "time": "after_market", "expected_eps": "$0.89", "whisper": "$0.94"}
  ],
  "risk_level_today": "HIGH",
  "recommendation": "Reduce position sizes before FOMC announcement"
}
```

---

### 🟡 Agente 1.3: Financial News Analyst

**Nombre en pixel office:** "Headlines"
**Personalidad:** Siempre leyendo, gafas puestas, rodeado de periódicos digitales. El intelectual del equipo.

**¿Qué investiga?**
- Breaking news financieras (mergers, acquisitions, bankruptcies)
- Cambios regulatorios (SEC, nuevas leyes, sanciones)
- Geopolítica que afecta mercados (guerras, sanciones, acuerdos comerciales)
- Sector-specific news (tech, healthcare, energy, etc.)
- Análisis de sentimiento de cada noticia
- Conexiones entre noticias aparentemente no relacionadas

**¿De dónde saca la info?**

| Fuente | API/Método | Costo | Datos |
|--------|-----------|-------|-------|
| Finnhub Market News | REST API | Free: 60 calls/min | General, forex, crypto news |
| Alpha Vantage News Sentiment | REST API | Free/Premium | News + AI sentiment scores |
| NewsAPI.ai | REST API | Free: 200 req/día | 500K+ fuentes, sentiment, entities |
| EODHD Financial News | REST API | Free tier | Stock-specific news + sentiment |
| Yahoo Finance News | yfinance Python | Gratis | Company-specific news |
| Google News | RSS feeds | Gratis | Broad financial news |

**Output que genera:**
```json
{
  "agent": "news_analyst",
  "timestamp": "2026-03-18T10:15:00Z",
  "breaking_news": [
    {
      "headline": "NVIDIA Announces $10B AI Chip Partnership with Microsoft",
      "source": "Reuters",
      "tickers_affected": ["NVDA", "MSFT"],
      "sentiment": 0.92,
      "impact_prediction": "HIGH_POSITIVE",
      "sector": "Technology",
      "analysis": "This partnership signals accelerating AI infrastructure spending..."
    }
  ],
  "geopolitical_alerts": [],
  "regulatory_changes": [],
  "sector_sentiment": {
    "Technology": 0.82,
    "Healthcare": 0.45,
    "Energy": -0.12
  }
}
```

---

### 🔴 Agente 1.4: Technical Data Collector

**Nombre en pixel office:** "Charts"
**Personalidad:** Silencioso, analítico, siempre mirando gráficos. Tiene 6 monitores en su escritorio.

**¿Qué investiga?**
- Price action en tiempo real (OHLCV)
- Indicadores técnicos: RSI, MACD, Bollinger Bands, EMA, SMA, ATR, Stochastic
- Niveles de soporte y resistencia
- Patrones de velas (doji, hammer, engulfing, etc.)
- Volumen y anomalías de volumen
- Order flow y depth of book (cuando disponible)
- Fibonacci retracements
- Market structure (higher highs, lower lows)

**¿De dónde saca la info?**

| Fuente | API/Método | Costo | Datos |
|--------|-----------|-------|-------|
| Alpaca Market Data | REST + WebSocket | Free (paper) | Real-time stocks, crypto OHLCV |
| Alpha Vantage Technical | REST API | Free/Premium | 50+ indicadores precalculados |
| Yahoo Finance (yfinance) | Python lib | Gratis | Históricos + intraday |
| TA-Lib | Python lib local | Gratis | 150+ indicadores calculados localmente |
| TradingView Lightweight Charts | Widget + data | Gratis | Visualización en la UI |
| FXCM API | REST API | Gratis (demo) | Forex real-time + históricos |

**Output que genera:**
```json
{
  "agent": "technical_collector",
  "timestamp": "2026-03-18T10:30:00Z",
  "ticker": "NVDA",
  "timeframe": "1H",
  "price": {"open": 142.50, "high": 145.20, "low": 141.80, "close": 144.90, "volume": 12500000},
  "indicators": {
    "RSI_14": 68.5,
    "MACD": {"macd": 1.23, "signal": 0.98, "histogram": 0.25},
    "BB": {"upper": 148.00, "middle": 143.50, "lower": 139.00},
    "EMA_20": 142.10,
    "EMA_50": 138.75,
    "ATR_14": 3.45
  },
  "patterns_detected": ["bullish_engulfing", "ascending_triangle"],
  "support_levels": [140.00, 137.50, 135.00],
  "resistance_levels": [146.00, 148.50, 150.00],
  "volume_analysis": "above_average_+35%",
  "trend": "UPTREND"
}
```

---

### 🟣 Agente 1.5: Fundamental Data Miner

**Nombre en pixel office:** "The Accountant"
**Personalidad:** Formal, con traje, siempre revisando números y hojas de balance. El más serio del equipo.

**¿Qué investiga?**
- Financial statements (income, balance sheet, cash flow)
- Ratios: P/E, P/B, P/S, debt-to-equity, ROE, ROA
- Revenue growth, margin trends
- Earnings surprises históricas
- Insider buying/selling
- Institutional ownership changes (13F filings)
- Analyst ratings y price targets
- Comparables del sector (peer analysis)
- DCF valuation estimates

**¿De dónde saca la info?**

| Fuente | API/Método | Costo | Datos |
|--------|-----------|-------|-------|
| Financial Modeling Prep | REST API | Free: 250 req/día | Statements, ratios, DCF, peers |
| Alpha Vantage Fundamentals | REST API | Free/Premium | Balance sheets, income, cash flow |
| Finnhub Company Profile | REST API | Free | Basic fundamentals, peers, metrics |
| SEC EDGAR | REST API | Gratis | 10-K, 10-Q, insider transactions |
| Yahoo Finance (yfinance) | Python lib | Gratis | Key stats, analyst recommendations |
| OpenBB Platform | Python lib | Gratis (open source) | Aggregates múltiples fuentes |

**Output que genera:**
```json
{
  "agent": "fundamental_miner",
  "timestamp": "2026-03-18T08:00:00Z",
  "ticker": "NVDA",
  "valuation": {
    "PE_ratio": 45.2,
    "PB_ratio": 28.5,
    "PS_ratio": 22.1,
    "PE_vs_sector_avg": "+15%",
    "DCF_fair_value": "$155.00",
    "current_price": "$144.90",
    "upside_potential": "+7%"
  },
  "financials": {
    "revenue_growth_yoy": "+62%",
    "net_margin": "55.2%",
    "debt_to_equity": 0.41,
    "free_cash_flow": "$22.8B",
    "ROE": "89.3%"
  },
  "insider_activity": {
    "last_30_days": {"buys": 3, "sells": 12, "net": "NET_SELLING"},
    "notable": "CFO sold $5M worth on 03/10"
  },
  "institutional": {
    "ownership_pct": 65.3,
    "change_last_quarter": "+2.1%",
    "top_buyers": ["Vanguard", "BlackRock"]
  },
  "analyst_consensus": {
    "rating": "STRONG_BUY",
    "avg_target": "$165.00",
    "high_target": "$200.00",
    "low_target": "$120.00"
  }
}
```

---

### 🟠 Agente 1.6: Crypto Intelligence Agent

**Nombre en pixel office:** "DeFi Dan"
**Personalidad:** Informal, hoodie, pegatinas en el laptop. El más joven del equipo. Habla en jerga crypto.

**¿Qué investiga?**
- Precios y volúmenes de top 100 cryptos
- Whale movements (transacciones grandes en blockchain)
- DeFi TVL (Total Value Locked) cambios
- Exchange inflows/outflows (señal de venta/compra)
- Bitcoin dominance y alt season indicators
- Fear & Greed Index crypto
- Funding rates en futuros (señal de overleveraged market)
- NFT market trends (como indicador de especulación)
- On-chain metrics (active addresses, hash rate, etc.)
- Nuevos listings en exchanges

**¿De dónde saca la info?**

| Fuente | API/Método | Costo | Datos |
|--------|-----------|-------|-------|
| CoinGecko API | REST API | Free: 30 req/min | Precios, volumen, market cap, trending |
| CoinGlass | REST API | Free tier | Funding rates, liquidations, open interest |
| Etherscan API | REST API | Free: 5 req/sec | ETH transactions, whale tracking |
| Blockchain.com API | REST API | Gratis | BTC on-chain metrics |
| DeFi Llama API | REST API | Gratis | TVL por protocolo, chain, etc. |
| Alternative.me | REST API | Gratis | Fear & Greed Index |
| Alpaca Crypto | REST API | Free (paper) | Crypto trading + market data |

**Output que genera:**
```json
{
  "agent": "crypto_intel",
  "timestamp": "2026-03-18T10:00:00Z",
  "market_overview": {
    "btc_price": 98432,
    "btc_dominance": "52.3%",
    "total_market_cap": "$3.8T",
    "fear_greed_index": 72,
    "fear_greed_label": "Greed"
  },
  "whale_alerts": [
    {"chain": "ETH", "amount": "$45M USDT", "from": "Binance", "to": "Unknown", "interpretation": "Possible large OTC buy incoming"}
  ],
  "defi_signals": {
    "total_tvl": "$185B",
    "tvl_change_24h": "+3.2%",
    "top_gaining_protocol": "Aave (+8.5%)"
  },
  "funding_rates": {
    "BTC_perp": "+0.012%",
    "ETH_perp": "+0.008%",
    "interpretation": "Slightly long-biased, not extreme"
  },
  "exchange_flows": {
    "btc_net_flow": "-2,340 BTC (outflow = bullish)",
    "eth_net_flow": "-12,500 ETH (outflow = bullish)"
  }
}
```

---

### 🔵 Agente 1.7: Forex & Macro Monitor

**Nombre en pixel office:** "Globe"
**Personalidad:** Viajero, tiene un mapa mundial en la pared. Habla de correlaciones entre países.

**¿Qué investiga?**
- Pares de divisas principales (EUR/USD, GBP/USD, USD/JPY, etc.)
- Correlaciones entre forex y otros mercados
- Carry trade opportunities
- Spreads y volatilidad
- DXY (Dollar Index) como indicador macro
- Yield curves de bonos (inversión = recesión signal)
- Commodities correlacionadas (Gold, Oil)
- COT reports (Commitment of Traders)

**¿De dónde saca la info?**

| Fuente | API/Método | Costo | Datos |
|--------|-----------|-------|-------|
| FXCM API | REST API | Gratis (demo account) | Forex real-time, históricos, ejecución demo |
| Alpha Vantage Forex | REST API | Free/Premium | Forex rates, intraday, daily |
| OANDA API | REST API | Free (practice account) | Forex data + paper trading |
| Forex News API | REST API | Free tier | Forex news + economic events |
| FRED API (St. Louis Fed) | REST API | Gratis | Yield curves, economic data US |
| Finnhub Forex | REST API | Free | Real-time forex rates |

**Output que genera:**
```json
{
  "agent": "forex_macro",
  "timestamp": "2026-03-18T10:00:00Z",
  "major_pairs": {
    "EUR/USD": {"price": 1.0834, "change_24h": "-0.15%", "trend": "bearish"},
    "USD/JPY": {"price": 149.25, "change_24h": "+0.32%", "trend": "bullish"},
    "GBP/USD": {"price": 1.2710, "change_24h": "-0.08%", "trend": "neutral"}
  },
  "dxy_index": {"value": 104.52, "trend": "strengthening"},
  "yield_curve": {
    "2Y": "4.35%",
    "10Y": "4.15%",
    "spread_2_10": "-0.20%",
    "interpretation": "INVERTED - recession signal still active"
  },
  "commodities": {
    "Gold": {"price": 2185, "trend": "bullish", "correlation_note": "Inverse to DXY"},
    "Oil_WTI": {"price": 78.50, "trend": "neutral"}
  },
  "cross_market_signals": [
    "Strong dollar pressuring emerging markets",
    "Gold rally suggests flight to safety despite equity strength"
  ]
}
```

---

### 🟤 Agente 1.8: Reddit & Community Sentiment

**Nombre en pixel office:** "Ape"
**Personalidad:** Casual, memes en su escritorio, detecta el "vibe" de la comunidad retail.

**¿Qué investiga?**
- r/wallstreetbets: hot posts, most mentioned tickers, YOLO sentiment
- r/stocks: more serious analysis posts
- r/cryptocurrency: crypto community sentiment
- r/forex: forex community strategies
- r/options: unusual options activity discussed
- r/investing: long-term sentiment shifts
- StockTwits: real-time trader sentiment
- Discord trading communities (cuando sea posible)
- "Meme stock" detection (unusual retail interest spikes)

**¿De dónde saca la info?**

| Fuente | API/Método | Costo | Datos |
|--------|-----------|-------|-------|
| Reddit API (OAuth) | REST API | Gratis | Posts, comments, upvotes |
| Finnhub Social Sentiment | REST API | Free | Reddit + Twitter sentiment aggregated |
| StockGeist | REST API | Free tier | Pre-processed social sentiment |
| PRAW (Python Reddit Wrapper) | Python lib | Gratis | Full Reddit access |
| StockTwits API | REST API | Gratis | Trader sentiment, trending |

**Output que genera:**
```json
{
  "agent": "reddit_sentiment",
  "timestamp": "2026-03-18T10:45:00Z",
  "wsb_top_tickers": [
    {"ticker": "GME", "mentions_24h": 890, "sentiment": 0.85, "trend": "YOLO_MODE"},
    {"ticker": "NVDA", "mentions_24h": 567, "sentiment": 0.72, "trend": "bullish"},
    {"ticker": "AAPL", "mentions_24h": 234, "sentiment": 0.55, "trend": "neutral"}
  ],
  "retail_interest_spikes": [
    {"ticker": "PLTR", "spike_pct": "+450%", "reason": "New government contract rumor"}
  ],
  "community_mood": {
    "wsb": "euphoric",
    "stocks": "cautiously_optimistic",
    "crypto": "greedy"
  },
  "meme_stock_alert": true,
  "warning": "High retail euphoria historically precedes corrections"
}
```

---

### ⚪ Agente 1.9: Alternative Data Scout

**Nombre en pixel office:** "Recon"
**Personalidad:** Misterioso, busca información que otros no ven. El espía de la oficina.

**¿Qué investiga?**
- Unusual options activity (large bets, unusual volume)
- Dark pool activity (institutional hidden trades)
- Short interest changes
- ETF flows (dinero entrando/saliendo de sectores)
- VIX (Fear Index) y sus derivados
- Put/Call ratios
- Sector rotation signals
- Earnings whisper numbers (vs consensus)
- Political event trading signals (elections, policy changes)

**¿De dónde saca la info?**

| Fuente | API/Método | Costo | Datos |
|--------|-----------|-------|-------|
| Finnhub | REST API | Free | Options activity, short interest |
| Alpha Vantage | REST API | Free/Premium | Broad market indicators |
| Financial Modeling Prep | REST API | Free: 250 req/día | ETF flows, institutional holdings |
| CBOE (VIX data) | Web scraping | Gratis | VIX, put/call ratios |
| Quiver Quantitative | API | Free tier | Political data, unusual activity |
| SEC EDGAR | REST API | Gratis | Short interest reports |

**Output que genera:**
```json
{
  "agent": "alt_data_scout",
  "timestamp": "2026-03-18T11:00:00Z",
  "unusual_options": [
    {"ticker": "NVDA", "type": "CALL", "strike": 160, "expiry": "2026-04-17", "volume": 45000, "oi": 5000, "signal": "VERY_BULLISH"}
  ],
  "vix": {"value": 18.5, "change": "-0.8", "interpretation": "Complacency, watch for spike"},
  "put_call_ratio": {"value": 0.72, "interpretation": "Bullish (below 1.0)"},
  "short_interest_changes": [
    {"ticker": "TSLA", "short_pct": "4.2%", "change": "-0.5%", "signal": "Short covering (bullish)"}
  ],
  "sector_rotation": {
    "money_flowing_in": ["Technology", "Healthcare"],
    "money_flowing_out": ["Utilities", "Consumer Staples"],
    "interpretation": "Risk-on environment"
  },
  "dark_pool_signals": [
    {"ticker": "AAPL", "volume": "$250M", "interpretation": "Large institutional accumulation"}
  ]
}
```

---

## DEPARTAMENTO 2: ANÁLISIS (Analysis Floor)

> **Misión:** Procesar toda la información cruda de los Investigadores, encontrar patrones, y debatir perspectivas alcistas vs bajistas.

---

### 🧠 Agente 2.1: Sentiment Fusion Engine

**Nombre en pixel office:** "Mood Ring"
**Rol:** Combina TODOS los sentimientos de diferentes fuentes en un score unificado.

**Recibe info de:** Twitter Scout, Reddit Sentiment, News Analyst, Crypto Intel
**Método:** FinBERT (NLP financiero) + weighted scoring

**Proceso:**
1. Recibe sentiment scores de cada fuente
2. Aplica pesos: News (30%), Twitter (25%), Reddit (20%), Options flow (15%), Other (10%)
3. Detecta discrepancias (ej: Twitter bullish pero institucionales vendiendo)
4. Genera alertas de "divergencia de sentimiento"
5. Score final: -100 (extreme fear) a +100 (extreme greed)

---

### 📊 Agente 2.2: Technical Analyst Pro

**Nombre en pixel office:** "Pattern Master"
**Rol:** Analiza profundamente los datos técnicos y genera señales de trading.

**Recibe info de:** Technical Data Collector
**Herramientas:** TA-Lib + custom pattern recognition + multi-timeframe analysis

**Proceso:**
1. Analiza múltiples timeframes (5min, 15min, 1H, 4H, Daily, Weekly)
2. Identifica confluencia de señales
3. Calcula probabilidad de dirección basado en patrones históricos
4. Define niveles exactos: Entry, Stop-Loss, Take-Profit 1/2/3
5. Risk/Reward ratio para cada setup

---

### 📈 Agente 2.3: Bullish Researcher (El Toro)

**Nombre en pixel office:** "Bull"
**Rol:** Abogado del diablo PRO-compra. Presenta el mejor caso alcista posible.

**Recibe info de:** Todos los agentes de investigación + análisis
**Herramienta:** LLM (Claude/GPT) con prompt de "find every reason to buy"

**Proceso (inspirado en TradingAgents debate mechanism):**
1. Recibe todos los datos recopilados
2. Construye el caso más fuerte posible para COMPRAR
3. Identifica catalizadores positivos
4. Argumenta contra los riesgos identificados
5. Presenta su caso al debate

---

### 📉 Agente 2.4: Bearish Researcher (El Oso)

**Nombre en pixel office:** "Bear"
**Rol:** Abogado del diablo PRO-venta. Presenta el mejor caso bajista posible.

**Recibe info de:** Todos los agentes de investigación + análisis
**Herramienta:** LLM (Claude/GPT) con prompt de "find every reason NOT to buy"

**Proceso:**
1. Recibe todos los datos recopilados
2. Construye el caso más fuerte posible para NO COMPRAR / VENDER
3. Identifica red flags y riesgos ocultos
4. Busca precedentes históricos de fracaso
5. Presenta su caso al debate

---

### ⚖️ Agente 2.5: Market Correlator & Cross-Asset Analyst

**Nombre en pixel office:** "The Bridge"
**Rol:** Encuentra relaciones ocultas entre mercados.

**Recibe info de:** Forex Monitor, Crypto Intel, Technical Collector, Alt Data Scout

**Proceso:**
1. Correlación entre DXY y stocks/crypto
2. Correlación entre yields y equities
3. Correlación entre VIX y oportunidades
4. Sector rotation signals
5. Cross-market divergences (ej: Bitcoin subiendo pero tech stocks bajando = señal)

---

## DEPARTAMENTO 3: ESTRATEGIA (Strategy Room)

---

### 🎯 Agente 3.1: Strategy Planner ("The Architect")

**Nombre en pixel office:** "The Architect"
**Rol:** Sintetiza TODO en un plan de trading coherente.

**Proceso:**
1. Recibe reportes de TODOS los departamentos
2. Modera el debate Bull vs Bear (configurable: 2-5 rounds)
3. Evalúa la fuerza de cada argumento
4. Identifica las TOP 3-5 mejores oportunidades
5. Asigna: Mercado (Stock/Crypto/Forex), Dirección (Long/Short), Tamaño sugerido, Timeframe
6. Pasa el plan al Report Writer

---

### 📝 Agente 3.2: Report Writer ("The Scribe")

**Nombre en pixel office:** "The Scribe"
**Rol:** Crea un documento profesional completo con toda la información.

**El reporte incluye:**
1. Executive Summary (1 párrafo)
2. Market Overview (condiciones generales)
3. Opportunity Analysis (cada trade propuesto con detalle)
4. Technical Setup (gráficos y niveles)
5. Fundamental Justification
6. Sentiment Landscape
7. Risk Assessment
8. Specific Trade Parameters:
   - Entry price / zone
   - Stop-loss level
   - Take-profit targets (TP1, TP2, TP3)
   - Position size recommendation
   - Risk/Reward ratio
   - Confidence score
9. Bull vs Bear Debate Summary
10. Final Recommendation

---

## DEPARTAMENTO 4: DECISIÓN Y RIESGO (Executive Suite)

---

### 🛡️ Agente 4.1: Risk Manager ("The Shield")

**Nombre en pixel office:** "The Shield"
**Rol:** Evalúa riesgo de cada propuesta contra el portfolio actual.

**Evalúa:**
- Maximum drawdown risk
- Correlation con posiciones existentes (no over-expose a un sector)
- Volatilidad actual del mercado (VIX)
- Event risk (¿hay FOMC hoy?)
- Position sizing con Kelly Criterion
- Maximum portfolio heat (total risk across all positions)
- Liquidity risk

---

### 👔 Agente 4.2: Decision Chief ("The Boss")

**Nombre en pixel office:** "The Boss"
**Rol:** El jefe final de IA. Revisa todo y da el veredicto.

**Proceso:**
1. Lee el reporte completo
2. Revisa el risk assessment
3. Evalúa contra las reglas del trading plan personal
4. Da veredicto: **BUY / SELL / HOLD / SKIP**
5. Explica razonamiento en lenguaje simple
6. Asigna confidence score final (0-100)
7. Si confidence > threshold → Envía alerta al humano

---

### 🔔 Agente 4.3: Human Interface ("The Messenger")

**Nombre en pixel office:** "The Messenger"
**Rol:** Comunica la decisión al humano y gestiona la aprobación.

**Canales de notificación:**
- Dashboard UI (principal)
- Telegram bot (mobile alerts)
- Email (resumen diario)
- Desktop notification

**Lo que muestra al humano:**
- Resumen en 3 líneas
- Ticker + Dirección + Confidence
- Botones: [✅ APROBAR] [❌ RECHAZAR] [📄 VER REPORTE] [✏️ MODIFICAR]

---

## DEPARTAMENTO 5: EJECUCIÓN (Trading Desk)

---

### ⚡ Agente 5.1: Trade Executor ("The Trigger")

**Nombre en pixel office:** "The Trigger"
**Rol:** Ejecuta trades SOLO después de aprobación humana.

**Brokers/APIs de ejecución (paper trading):**

| Broker | Mercado | API | Paper Trading | Costo |
|--------|---------|-----|---------------|-------|
| Alpaca | Stocks + Crypto + Options | REST + MCP Server | ✅ Sí, gratis | $0 |
| FXCM | Forex | REST API | ✅ Sí, demo account | $0 |
| OANDA | Forex | REST API | ✅ Practice account | $0 |
| Alpaca Crypto | Crypto | REST API | ✅ Paper mode | $0 |

**Funciones:**
- Ejecuta la orden según los parámetros aprobados
- Coloca stop-loss y take-profit automáticamente
- Monitorea llenado de órdenes
- Reporta estado al dashboard

---

### 📊 Agente 5.2: Position Monitor ("The Watchdog")

**Nombre en pixel office:** "The Watchdog"
**Rol:** Monitorea posiciones abiertas 24/7.

**Funciones:**
- Tracking de P&L en tiempo real
- Trailing stop-loss management
- Alerta si una posición se acerca a stop-loss
- Alerta de take-profit reached
- Monitorea cambios de condiciones que afecten posiciones abiertas

---

## DEPARTAMENTO 6: APRENDIZAJE (Research Lab) 🆕

> **Este departamento NO existe en TradingAgents original. Es nuestra innovación.**

---

### 🧪 Agente 6.1: Backtester ("The Historian")

**Nombre en pixel office:** "The Historian"
**Rol:** Prueba las estrategias contra datos históricos.

**Frameworks de backtesting:**

| Framework | Tipo | Costo | Best For |
|-----------|------|-------|----------|
| VectorBT PRO | Vectorized | Premium | Ultra-fast research, robustness analysis |
| Backtesting.py | Event-driven | Gratis | Fast prototyping, reports |
| Zipline-Reloaded | Pipeline | Gratis | Pipeline-style research |
| NautilusTrader | Production | Gratis | Production-first workflows |

**Proceso:**
1. Toma cada decisión que el sistema generó
2. Simula con datos históricos: ¿habría funcionado?
3. Calcula métricas: Sharpe ratio, max drawdown, win rate, profit factor
4. Identifica en qué condiciones de mercado funciona mejor/peor
5. Genera "strategy report card"

---

### 🧬 Agente 6.2: Learning Engine ("The Professor")

**Nombre en pixel office:** "The Professor"
**Rol:** APRENDE de los errores y éxitos para mejorar continuamente.

**Sistema de feedback loop:**

```
Trade ejecutado → Resultado (ganó/perdió)
         ↓
Análisis post-mortem:
- ¿Qué agente dio la señal correcta/incorrecta?
- ¿Qué fuente de datos fue más confiable?
- ¿En qué condiciones de mercado falló?
- ¿El tamaño de posición fue correcto?
         ↓
Ajustes automáticos:
- Pesos de cada agente (si Twitter Scout acierta más → más peso)
- Thresholds de confianza (si muchos trades con 60% confidence fallan → subir threshold)
- Parámetros de indicadores técnicos
         ↓
"Strategy Graveyard":
- Catálogo de estrategias que fallaron
- Patrones de overfitting detectados
- Registro de TODAS las decisiones para análisis futuro
```

**Almacenamiento:**
- SQLite/PostgreSQL para todas las decisiones y resultados
- Vector DB (ChromaDB) para búsqueda semántica de situaciones similares
- Dashboard de performance por agente, mercado, y timeframe

---

## RESUMEN DE APIs Y COSTOS TOTALES

### Tier Gratuito (Paper Trading Completo)

| Servicio | Uso | Costo |
|----------|-----|-------|
| Alpaca (paper) | Stocks, crypto, ejecución | $0 |
| FXCM (demo) | Forex data + paper trading | $0 |
| Alpha Vantage (free) | 25 req/día, datos fundamentales | $0 |
| CoinGecko | 30 req/min, crypto data | $0 |
| Finnhub (free) | 60 req/min, news, sentiment, calendar | $0 |
| Financial Modeling Prep (free) | 250 req/día, financials | $0 |
| Reddit API | Posts, comments, sentiment | $0 |
| Twitter API (basic) | 10K tweets/mes | $0 |
| NewsAPI (free) | 200 req/día | $0 |
| EODHD (free) | Calendar, news | $0 |
| Yahoo Finance (yfinance) | Unlimited | $0 |
| FRED API | Economic data US | $0 |
| DeFi Llama | TVL, DeFi data | $0 |
| Alternative.me | Fear & Greed crypto | $0 |
| TradingView Charts | Widgets gratis | $0 |
| TA-Lib | Indicadores técnicos | $0 |
| FinBERT | Sentiment NLP | $0 |
| OpenBB | Data aggregation | $0 |
| TradingAgents | Multi-agent framework | $0 |
| Agent Office | Pixel visualization | $0 |
| Backtesting.py | Backtesting | $0 |
| **Subtotal infraestructura** | | **$0** |
| Claude API (análisis LLM) | Pay per use | ~$10-30/mes |
| **TOTAL** | | **~$10-30/mes** |

### Si quieres upgrade a Premium:

| Upgrade | Beneficio | Costo |
|---------|-----------|-------|
| Alpha Vantage Premium | 75 req/min instead of 25/día | +$49.99/mes |
| Twitter API Pro | 1M tweets/mes | +$100/mes |
| Finnhub Premium | No rate limits, more data | +$50/mes |

---

## VISUAL: CÓMO SE VE EN EL PIXEL OFFICE

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        🏢 TRADINGAI CENTER                              │
│                        ══════════════════                                │
│                                                                          │
│  ┌─── RESEARCH FLOOR ──────────────────────────────────────────────┐    │
│  │                                                                  │    │
│  │  🔵X-Ray     🟢Scheduler   🟡Headlines   🔴Charts              │    │
│  │  [tweeting]  [checking]    [reading]     [charting]             │    │
│  │                                                                  │    │
│  │  🟣Accountant  🟠DeFi Dan  🔵Globe   🟤Ape    ⚪Recon          │    │
│  │  [calculating] [scanning]  [mapping]  [lurking] [investigating] │    │
│  │                                                                  │    │
│  └──────────────────────────── ↓ data flows down ──────────────────┘    │
│                                                                          │
│  ┌─── ANALYSIS FLOOR ─────────────────────────────────────────────┐    │
│  │                                                                  │    │
│  │  🧠Mood Ring    📊Pattern Master    🌉The Bridge               │    │
│  │  [fusing]       [analyzing]          [correlating]              │    │
│  │                                                                  │    │
│  │           📈Bull  ←── DEBATING ──→  📉Bear                     │    │
│  │          "I think      🗯️🗯️🗯️      "But what                 │    │
│  │           NVDA will..."              about the..."              │    │
│  │                                                                  │    │
│  └──────────────────────────── ↓ insights flow down ───────────────┘    │
│                                                                          │
│  ┌─── STRATEGY ROOM ─────────────────────────────────────────────┐     │
│  │                                                                  │    │
│  │       🎯The Architect  ──→  📝The Scribe                       │    │
│  │       [planning]            [writing report]                    │    │
│  │                                                                  │    │
│  └──────────────────────────── ↓ report flows down ────────────────┘    │
│                                                                          │
│  ┌─── EXECUTIVE SUITE ───────────────────────────────────────────┐     │
│  │                                                                  │    │
│  │   🛡️The Shield  →  👔The Boss  →  🔔The Messenger             │    │
│  │   [risk check]     [deciding]     [alerting YOU]               │    │
│  │                                                                  │    │
│  └──────────────────────────── ↓ awaiting your approval ───────────┘    │
│                                                                          │
│  ┌─── TRADING DESK ──────────────────────────────────────────────┐     │
│  │                                                                  │    │
│  │        ⚡The Trigger    📊The Watchdog                          │    │
│  │        [ready]          [monitoring]                             │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─── RESEARCH LAB ──────────────────────────────────────────────┐     │
│  │                                                                  │    │
│  │        🧪The Historian    🧬The Professor                       │    │
│  │        [backtesting]      [learning from results]               │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## PRÓXIMOS PASOS

1. **Validar este blueprint** - ¿Quieres agregar/quitar/modificar agentes?
2. **Elegir UI engine** - Agent Office (Phaser.js + Colyseus) vs Claw-Empire (PixiJS + Express)
3. **Configurar ambiente de desarrollo** - Python + Node.js + APIs
4. **Fase 1: Instalar TradingAgents** - como base funcional
5. **Fase 2: Extender con agentes custom** - los que no tiene el framework original
6. **Fase 3: Construir la UI Pixel Office** - adaptada para trading
7. **Fase 4: Integrar backtesting** - VectorBT + Backtesting.py
8. **Fase 5: Conectar ejecución** - Alpaca + FXCM paper trading
