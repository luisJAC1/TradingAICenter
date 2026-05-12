"""
Knowledge Bus — Redis pub/sub backbone for inter-agent communication.

Every agent publishes to and listens from this bus. No information silos.
Message schema matches the TradingAICenter architecture spec in CLAUDE.md.
"""

import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

import redis.asyncio as aioredis
from pydantic import BaseModel, Field

from config import settings

log = logging.getLogger(__name__)

CHANNEL_ALL = "bus:all"          # Every agent subscribes to this
CHANNEL_ALERTS = "bus:alerts"    # High-priority alerts
CHANNEL_PREFIX = "bus:agent:"    # bus:agent:<agent_id> — direct messages


class MessageType(str, Enum):
    BROADCAST = "broadcast"
    DIRECT_MESSAGE = "direct_message"
    REQUEST_INFO = "request_info"
    DEBATE_ROUND = "debate_round"
    ALERT = "alert"
    CONSENSUS_CHECK = "consensus_check"
    AGENT_STATUS = "agent_status"   # UI status updates


class MessageCategory(str, Enum):
    MARKET_DATA = "market_data"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    NEWS = "news"
    MACRO = "macro"
    CRYPTO = "crypto"
    FOREX = "forex"
    RISK = "risk"
    TRADE_SIGNAL = "trade_signal"
    ANALYSIS = "analysis"          # Dept 2 synthesized output
    ALTERNATIVE_DATA = "alternative_data"  # Recon: dark pools, unusual options, insiders
    SYSTEM = "system"
    STATUS = "status"


class BusMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    from_agent: str
    to_agent: str = "all"           # "all" = broadcast
    priority: int = 5               # 1 (highest) – 10 (lowest)
    type: MessageType = MessageType.BROADCAST
    category: MessageCategory = MessageCategory.SYSTEM
    tickers_relevant: list[str] = Field(default_factory=list)
    markets_affected: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0         # 0.0 – 1.0
    requires_response: bool = False
    thread_id: str | None = None


MessageHandler = Callable[[BusMessage], Awaitable[None]]


class KnowledgeBus:
    """Async Redis-backed pub/sub Knowledge Bus."""

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._handlers: dict[str, list[MessageHandler]] = {}
        self._listen_task: asyncio.Task | None = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(
            settings.redis_url, decode_responses=True
        )
        await self._redis.ping()
        self._pubsub = self._redis.pubsub()
        log.info("[KnowledgeBus] Connected to Redis at %s", settings.redis_url)

    async def disconnect(self) -> None:
        if self._listen_task:
            self._listen_task.cancel()
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.aclose()
        log.info("[KnowledgeBus] Disconnected")

    async def subscribe(self, agent_id: str, handler: MessageHandler) -> None:
        """Subscribe an agent to the global bus and its own direct channel."""
        channels = [CHANNEL_ALL, f"{CHANNEL_PREFIX}{agent_id}"]
        if agent_id not in self._handlers:
            self._handlers[agent_id] = []
        self._handlers[agent_id].append(handler)

        if self._pubsub:
            await self._pubsub.subscribe(*channels)
            log.debug("[KnowledgeBus] %s subscribed to %s", agent_id, channels)

        if self._listen_task is None or self._listen_task.done():
            self._listen_task = asyncio.create_task(self._listen_loop())

    async def publish(self, message: BusMessage) -> None:
        """Publish a message. Broadcasts go to CHANNEL_ALL; direct messages to agent channel."""
        if not self._redis:
            raise RuntimeError("KnowledgeBus not connected")

        raw = message.model_dump_json()

        if message.to_agent == "all":
            await self._redis.publish(CHANNEL_ALL, raw)
        else:
            await self._redis.publish(f"{CHANNEL_PREFIX}{message.to_agent}", raw)

        # Also store in Redis stream for replay / UI polling
        await self._redis.xadd(
            "bus:stream",
            {"data": raw},
            maxlen=1000,
            approximate=True,
        )
        log.debug("[KnowledgeBus] Published %s from %s", message.type, message.from_agent)

    async def get_recent_messages(self, count: int = 50) -> list[BusMessage]:
        """Return the last N messages from the stream (for UI polling)."""
        if not self._redis:
            return []
        entries = await self._redis.xrevrange("bus:stream", count=count)
        messages = []
        for _, fields in entries:
            try:
                messages.append(BusMessage.model_validate_json(fields["data"]))
            except Exception:
                pass
        return list(reversed(messages))

    async def _listen_loop(self) -> None:
        if not self._pubsub:
            return
        try:
            async for raw in self._pubsub.listen():
                if raw["type"] != "message":
                    continue
                try:
                    msg = BusMessage.model_validate_json(raw["data"])
                    await self._dispatch(msg)
                except Exception as exc:
                    log.warning("[KnowledgeBus] Bad message: %s", exc)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            log.error("[KnowledgeBus] Listen loop error: %s", exc)

    async def _dispatch(self, msg: BusMessage) -> None:
        for handlers in self._handlers.values():
            for handler in handlers:
                try:
                    await handler(msg)
                except Exception as exc:
                    log.error("[KnowledgeBus] Handler error: %s", exc)


# Singleton — shared across the entire Brain process
bus = KnowledgeBus()
