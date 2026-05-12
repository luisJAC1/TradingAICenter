"""
Unified market data layer — replaces yfinance.

Routes by symbol type:
- Stocks/ETFs        → Alpaca v2 (IEX feed, free)
- Crypto (BTC/ETH)   → Alpaca v1beta3 crypto (free)
- Forex pairs        → Frankfurter (ECB rates, free, no key)
- Macro instruments  → ETF proxies via Alpaca (UUP=DXY, VIXY=VIX, USO=oil, IEF=10Y, SHY=2Y)

Returns pandas DataFrames with Open/High/Low/Close/Volume columns
matching the shape the old yfinance code expects.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable

import httpx
import pandas as pd

from config import settings

log = logging.getLogger(__name__)

ALPACA_DATA_URL = "https://data.alpaca.markets"

# Macro tickers → ETF proxies served by Alpaca
MACRO_PROXY = {
    "DX-Y.NYB": "UUP",   # US Dollar Index → Invesco USD Bullish ETF
    "^VIX":     "VIXY",  # VIX → VIX Short-Term Futures ETF
    "GC=F":     "GLD",   # Gold futures → SPDR Gold
    "CL=F":     "USO",   # Crude oil → US Oil Fund
    "^TNX":     "IEF",   # 10Y yield → 7-10Y Treasury ETF (price inverse to yield)
    "^IRX":     "SHY",   # 13W bill → 1-3Y Treasury ETF (price inverse to yield)
}

# Yfinance forex tickers → Frankfurter (base, quote) tuples
FOREX_MAP = {
    "EURUSD=X": ("EUR", "USD"),
    "GBPUSD=X": ("GBP", "USD"),
    "JPY=X":    ("USD", "JPY"),
    "CAD=X":    ("USD", "CAD"),
    "AUDUSD=X": ("AUD", "USD"),
    "MXN=X":    ("USD", "MXN"),
}

# Crypto symbols → Alpaca format
CRYPTO_MAP = {
    "BTC-USD": "BTC/USD",
    "ETH-USD": "ETH/USD",
}


def _alpaca_headers() -> dict[str, str]:
    return {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
    }


def _resolution_to_alpaca(timeframe: str) -> str:
    """Map our internal interval strings to Alpaca timeframe."""
    return {
        "1h": "1Hour",
        "60m": "1Hour",
        "1d": "1Day",
        "1wk": "1Week",
        "1w": "1Week",
    }.get(timeframe, "1Day")


def _period_to_days(period: str) -> int:
    """Convert yfinance-style period to lookback days."""
    period = period.strip().lower()
    if period.endswith("d"):
        return int(period[:-1])
    if period.endswith("mo"):
        return int(period[:-2]) * 30
    if period.endswith("y"):
        return int(period[:-1]) * 365
    return 60


def _classify(symbol: str) -> str:
    if symbol in MACRO_PROXY:
        return "macro_proxy"
    if symbol in FOREX_MAP:
        return "forex"
    if symbol in CRYPTO_MAP or "-USD" in symbol or "/USD" in symbol:
        return "crypto"
    return "stock"


def _bars_to_df(bars: list[dict]) -> pd.DataFrame:
    """Convert Alpaca bars list to OHLCV DataFrame."""
    if not bars:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    rows = []
    for b in bars:
        rows.append({
            "datetime": pd.to_datetime(b["t"]),
            "Open":   float(b["o"]),
            "High":   float(b["h"]),
            "Low":    float(b["l"]),
            "Close":  float(b["c"]),
            "Volume": float(b.get("v", 0)),
        })
    df = pd.DataFrame(rows).set_index("datetime").sort_index()
    return df


def _fetch_alpaca_stocks(symbols: list[str], timeframe: str, days: int) -> dict[str, pd.DataFrame]:
    """Batch fetch stock/ETF bars from Alpaca."""
    if not symbols:
        return {}
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"{ALPACA_DATA_URL}/v2/stocks/bars"
    params = {
        "symbols": ",".join(symbols),
        "timeframe": _resolution_to_alpaca(timeframe),
        "start": start,
        "limit": 10000,
        "adjustment": "all",
        "feed": "iex",
    }
    out: dict[str, pd.DataFrame] = {}
    try:
        with httpx.Client(timeout=20.0) as client:
            page_token = None
            while True:
                if page_token:
                    params["page_token"] = page_token
                r = client.get(url, headers=_alpaca_headers(), params=params)
                r.raise_for_status()
                data = r.json()
                for sym, bars in (data.get("bars") or {}).items():
                    df_new = _bars_to_df(bars)
                    if sym in out:
                        out[sym] = pd.concat([out[sym], df_new])
                    else:
                        out[sym] = df_new
                page_token = data.get("next_page_token")
                if not page_token:
                    break
    except Exception as exc:
        log.warning("[market_data] Alpaca stocks fetch failed: %s", exc)
    return out


def _fetch_alpaca_crypto(symbols: list[str], timeframe: str, days: int) -> dict[str, pd.DataFrame]:
    """Batch fetch crypto bars from Alpaca."""
    if not symbols:
        return {}
    alpaca_syms = [CRYPTO_MAP.get(s, s.replace("-", "/")) for s in symbols]
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"{ALPACA_DATA_URL}/v1beta3/crypto/us/bars"
    params = {
        "symbols": ",".join(alpaca_syms),
        "timeframe": _resolution_to_alpaca(timeframe),
        "start": start,
        "limit": 10000,
    }
    out: dict[str, pd.DataFrame] = {}
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.get(url, headers=_alpaca_headers(), params=params)
            r.raise_for_status()
            data = r.json()
            # Map back: BTC/USD → BTC-USD
            reverse_map = {v: k for k, v in CRYPTO_MAP.items()}
            for sym, bars in (data.get("bars") or {}).items():
                original = reverse_map.get(sym, sym.replace("/", "-"))
                out[original] = _bars_to_df(bars)
    except Exception as exc:
        log.warning("[market_data] Alpaca crypto fetch failed: %s", exc)
    return out


def _fetch_forex(symbols: list[str], days: int) -> dict[str, pd.DataFrame]:
    """Fetch forex from Frankfurter (ECB daily rates, free)."""
    if not symbols:
        return {}
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)
    out: dict[str, pd.DataFrame] = {}

    # Group by base currency to minimize requests
    by_base: dict[str, list[tuple[str, str]]] = {}
    for sym in symbols:
        if sym not in FOREX_MAP:
            continue
        base, quote = FOREX_MAP[sym]
        by_base.setdefault(base, []).append((sym, quote))

    try:
        with httpx.Client(timeout=15.0) as client:
            for base, pairs in by_base.items():
                quotes = ",".join({q for _, q in pairs})
                url = f"https://api.frankfurter.dev/v1/{start}..{end}"
                r = client.get(url, params={"from": base, "to": quotes})
                if r.status_code != 200:
                    continue
                data = r.json().get("rates", {})
                # Build per-day rate series for each quote currency
                series_by_quote: dict[str, list[tuple[str, float]]] = {q: [] for _, q in pairs}
                for day, rates in sorted(data.items()):
                    for q in series_by_quote:
                        if q in rates:
                            series_by_quote[q].append((day, float(rates[q])))
                for sym, quote in pairs:
                    rows = series_by_quote.get(quote, [])
                    if not rows:
                        continue
                    df = pd.DataFrame(rows, columns=["datetime", "Close"])
                    df["datetime"] = pd.to_datetime(df["datetime"])
                    df["Open"] = df["Close"]
                    df["High"] = df["Close"]
                    df["Low"] = df["Close"]
                    df["Volume"] = 0.0
                    df = df.set_index("datetime").sort_index()
                    out[sym] = df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception as exc:
        log.warning("[market_data] Frankfurter forex fetch failed: %s", exc)
    return out


def fetch_bars(symbols: Iterable[str], timeframe: str = "1d",
               period: str = "60d") -> dict[str, pd.DataFrame]:
    """
    Unified OHLCV fetch — replaces yf.download(...).

    Args:
        symbols: tickers in yfinance-style notation (AAPL, BTC-USD, ^VIX, EURUSD=X, etc.)
        timeframe: "1h", "1d", "1wk"
        period: "60d", "1y", "5y" etc.

    Returns:
        dict mapping original symbol → DataFrame with Open/High/Low/Close/Volume columns
    """
    symbols = list(symbols)
    days = _period_to_days(period)

    by_kind: dict[str, list[str]] = {"stock": [], "crypto": [], "forex": [], "macro_proxy": []}
    for s in symbols:
        by_kind[_classify(s)].append(s)

    out: dict[str, pd.DataFrame] = {}

    # Stocks (direct)
    if by_kind["stock"]:
        out.update(_fetch_alpaca_stocks(by_kind["stock"], timeframe, days))

    # Macro proxies (ETFs via Alpaca) — fetch under proxy symbol, store under original
    if by_kind["macro_proxy"]:
        proxies = [MACRO_PROXY[s] for s in by_kind["macro_proxy"]]
        proxy_data = _fetch_alpaca_stocks(proxies, timeframe, days)
        for original in by_kind["macro_proxy"]:
            proxy = MACRO_PROXY[original]
            if proxy in proxy_data:
                df = proxy_data[proxy].copy()
                # Yield ETFs are inverse to yields — flag for downstream agents
                if original in ("^TNX", "^IRX"):
                    df.attrs["yield_inverse"] = True
                out[original] = df

    # Crypto via Alpaca
    if by_kind["crypto"]:
        out.update(_fetch_alpaca_crypto(by_kind["crypto"], timeframe, days))

    # Forex via Frankfurter
    if by_kind["forex"]:
        out.update(_fetch_forex(by_kind["forex"], days))

    return out


def fetch_bars_multiindex(symbols: Iterable[str], timeframe: str = "1d",
                          period: str = "60d") -> pd.DataFrame:
    """
    Returns a MultiIndex DataFrame matching yfinance's group_by='ticker' format.
    Outer level = ticker, inner level = OHLCV column.
    """
    by_symbol = fetch_bars(symbols, timeframe, period)
    if not by_symbol:
        return pd.DataFrame()
    frames = []
    for sym, df in by_symbol.items():
        if df.empty:
            continue
        df_copy = df.copy()
        df_copy.columns = pd.MultiIndex.from_product([[sym], df_copy.columns])
        frames.append(df_copy)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1).sort_index()


def fetch_quotes(symbols: Iterable[str]) -> dict[str, dict]:
    """
    Fast current-price quotes for stocks/ETFs via Finnhub.
    Returns {symbol: {price, change, change_pct, prev_close, high, low}}.
    """
    out: dict[str, dict] = {}
    if not settings.finnhub_api_key:
        return out
    try:
        with httpx.Client(timeout=10.0) as client:
            for sym in symbols:
                if _classify(sym) != "stock":
                    continue
                r = client.get(
                    "https://finnhub.io/api/v1/quote",
                    params={"symbol": sym, "token": settings.finnhub_api_key},
                )
                if r.status_code != 200:
                    continue
                d = r.json()
                if d.get("c"):
                    out[sym] = {
                        "price": d["c"],
                        "change": d.get("d", 0),
                        "change_pct": d.get("dp", 0),
                        "prev_close": d.get("pc", 0),
                        "high": d.get("h", 0),
                        "low": d.get("l", 0),
                    }
    except Exception as exc:
        log.debug("[market_data] Finnhub quotes failed: %s", exc)
    return out


def fetch_forex(pairs: Iterable[str]) -> dict[str, dict]:
    """Wrapper around _fetch_forex for current snapshot."""
    bars = _fetch_forex(list(pairs), days=5)
    out = {}
    for sym, df in bars.items():
        if df.empty or len(df) < 2:
            continue
        closes = df["Close"].dropna()
        if len(closes) < 2:
            continue
        price = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])
        out[sym] = {
            "rate": round(price, 5),
            "change_1d_pct": round((price / prev - 1) * 100, 3),
        }
    return out
