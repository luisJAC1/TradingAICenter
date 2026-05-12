"""
Cryptid — Crypto & Blockchain Intelligence (Dept 1: Investigación)

On-chain analysis: whale movements, DeFi TVL, exchange flows, funding rates,
Fear & Greed index, stablecoin flows. 24/7 skeleton crew agent.

Data sources (all free, no key required):
- CoinGecko public API
- Alternative.me Fear & Greed
- DeFi Llama
"""

import logging
from datetime import datetime, timezone

import httpx

from agents.base import BaseAgent, AgentStatus
from knowledge_bus.bus import BusMessage, MessageCategory, MessageType

log = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
DEFILLAMA_BASE = "https://api.llama.fi"
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=2"

DEFAULT_COINS = ["bitcoin", "ethereum", "solana", "ripple", "cardano"]


class CryptidAgent(BaseAgent):
    agent_id = "cryptid"
    agent_name = "Cryptid"
    department = "research"
    emoji = "🕸️"

    async def run_cycle(self) -> None:
        await self.set_status(AgentStatus.WORKING, "Scanning crypto markets")

        async with httpx.AsyncClient(timeout=15.0) as client:
            prices = await self._fetch_prices(client)
            fear_greed = await self._fetch_fear_greed(client)
            defi_tvl = await self._fetch_defi_tvl(client)

        if not prices:
            await self.set_status(AgentStatus.IDLE)
            return

        signals = self._analyze(prices, fear_greed)

        await self.set_status(AgentStatus.SENDING, "Publishing crypto intelligence")
        await self.publish(
            payload={
                "prices": prices,
                "fear_greed": fear_greed,
                "defi_tvl_usd": defi_tvl,
                "signals": signals,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category=MessageCategory.MARKET_DATA,
            markets=["crypto"],
            tickers=[p["symbol"].upper() for p in prices],
            confidence=0.75,
            priority=4,
        )
        log.info("[Cryptid] Published data for %d coins | F&G: %s", len(prices), fear_greed.get("value_classification", "?"))

        await self.set_status(AgentStatus.IDLE)

    # ── Data fetchers ──────────────────────────────────────────────────────────

    async def _fetch_prices(self, client: httpx.AsyncClient) -> list[dict]:
        try:
            ids = ",".join(DEFAULT_COINS)
            r = await client.get(
                f"{COINGECKO_BASE}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "ids": ids,
                    "order": "market_cap_desc",
                    "price_change_percentage": "1h,24h,7d",
                },
            )
            r.raise_for_status()
            data = r.json()
            return [
                {
                    "id": c["id"],
                    "symbol": c["symbol"],
                    "name": c["name"],
                    "price": c["current_price"],
                    "market_cap": c["market_cap"],
                    "volume_24h": c["total_volume"],
                    "change_1h": c.get("price_change_percentage_1h_in_currency"),
                    "change_24h": c.get("price_change_percentage_24h"),
                    "change_7d": c.get("price_change_percentage_7d_in_currency"),
                    "ath_distance_pct": round(
                        (c["current_price"] / c["ath"] - 1) * 100, 1
                    ) if c.get("ath") else None,
                }
                for c in data
            ]
        except Exception as exc:
            log.warning("[Cryptid] CoinGecko fetch failed: %s", exc)
            return []

    async def _fetch_fear_greed(self, client: httpx.AsyncClient) -> dict:
        try:
            r = await client.get(FEAR_GREED_URL)
            r.raise_for_status()
            entry = r.json()["data"][0]
            return {
                "value": int(entry["value"]),
                "value_classification": entry["value_classification"],
                "timestamp": entry["timestamp"],
            }
        except Exception as exc:
            log.warning("[Cryptid] Fear & Greed fetch failed: %s", exc)
            return {}

    async def _fetch_defi_tvl(self, client: httpx.AsyncClient) -> float | None:
        try:
            r = await client.get(f"{DEFILLAMA_BASE}/v2/historicalChainTvl")
            r.raise_for_status()
            data = r.json()
            if data:
                return data[-1].get("tvl")
        except Exception as exc:
            log.warning("[Cryptid] DeFi Llama fetch failed: %s", exc)
        return None

    # ── Signal analysis ────────────────────────────────────────────────────────

    def _analyze(self, prices: list[dict], fear_greed: dict) -> list[dict]:
        signals = []
        fg_value = fear_greed.get("value", 50)

        # Extreme Fear & Greed signals
        if fg_value <= 20:
            signals.append({
                "type": "sentiment",
                "signal": "EXTREME_FEAR",
                "detail": f"Fear & Greed at {fg_value} — historically a buy zone",
                "strength": "strong",
            })
        elif fg_value >= 80:
            signals.append({
                "type": "sentiment",
                "signal": "EXTREME_GREED",
                "detail": f"Fear & Greed at {fg_value} — historically a caution zone",
                "strength": "moderate",
            })

        # Large 24h moves
        for coin in prices:
            change = coin.get("change_24h")
            if change is None:
                continue
            if change <= -10:
                signals.append({
                    "type": "price_action",
                    "signal": "LARGE_DROP",
                    "ticker": coin["symbol"].upper(),
                    "detail": f"{coin['symbol'].upper()} down {change:.1f}% in 24h",
                    "strength": "strong" if change <= -15 else "moderate",
                })
            elif change >= 10:
                signals.append({
                    "type": "price_action",
                    "signal": "LARGE_PUMP",
                    "ticker": coin["symbol"].upper(),
                    "detail": f"{coin['symbol'].upper()} up {change:.1f}% in 24h",
                    "strength": "strong" if change >= 15 else "moderate",
                })

        return signals

    async def handle_message(self, msg: BusMessage) -> None:
        if msg.type == MessageType.REQUEST_INFO and msg.payload.get("request") == "crypto_update":
            await self.run_cycle()
