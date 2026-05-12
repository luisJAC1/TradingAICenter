"""
Semantic Memory — ChromaDB vector store.

Gives agents the ability to say: "I've seen this situation before — here's what happened."
Every significant market event, trade signal, and analysis is stored here.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings as app_settings

log = logging.getLogger(__name__)

COLLECTION_MARKET_EVENTS = "market_events"
COLLECTION_TRADE_SIGNALS = "trade_signals"
COLLECTION_AGENT_INSIGHTS = "agent_insights"


class SemanticMemory:
    """Wrapper around ChromaDB for semantic search across historical market context."""

    def __init__(self) -> None:
        self._client: chromadb.AsyncHttpClient | None = None
        self._collections: dict[str, Any] = {}

    async def connect(self) -> None:
        try:
            self._client = await chromadb.AsyncHttpClient(
                host=app_settings.chroma_host,
                port=app_settings.chroma_port,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    chroma_api_impl="chromadb.api.fastapi.FastAPI",
                ),
            )
            await self._client.heartbeat()

            # Pre-create collections
            for name in [COLLECTION_MARKET_EVENTS, COLLECTION_TRADE_SIGNALS, COLLECTION_AGENT_INSIGHTS]:
                self._collections[name] = await self._client.get_or_create_collection(name)

            log.info(
                "[SemanticMemory] Connected to ChromaDB at %s:%d",
                app_settings.chroma_host,
                app_settings.chroma_port,
            )
        except Exception as exc:
            log.warning("[SemanticMemory] ChromaDB unavailable: %s — running without semantic memory", exc)

    async def store_event(
        self,
        text: str,
        *,
        collection: str = COLLECTION_MARKET_EVENTS,
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> str | None:
        """Store a market event / insight for future semantic recall."""
        col = self._collections.get(collection)
        if col is None:
            return None
        try:
            doc_id = doc_id or str(uuid.uuid4())
            meta = metadata or {}
            meta["timestamp"] = datetime.now(timezone.utc).isoformat()
            await col.add(documents=[text], metadatas=[meta], ids=[doc_id])
            return doc_id
        except Exception as exc:
            log.debug("[SemanticMemory] store_event error: %s", exc)
            return None

    async def recall(
        self,
        query: str,
        *,
        collection: str = COLLECTION_MARKET_EVENTS,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Find the most similar past events to the given query."""
        col = self._collections.get(collection)
        if col is None:
            return []
        try:
            results = await col.query(query_texts=[query], n_results=n_results)
            output = []
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            for doc, meta, dist in zip(docs, metas, distances):
                output.append({
                    "text": doc,
                    "metadata": meta,
                    "similarity": round(1 - dist, 4),  # convert distance → similarity
                })
            return output
        except Exception as exc:
            log.debug("[SemanticMemory] recall error: %s", exc)
            return []

    async def store_trade_signal(self, signal: dict[str, Any]) -> str | None:
        text = (
            f"Trade signal: {signal.get('ticker')} {signal.get('direction')} "
            f"at {signal.get('price')}. Confidence: {signal.get('confidence')}. "
            f"Reasoning: {signal.get('reasoning', '')}"
        )
        return await self.store_event(
            text,
            collection=COLLECTION_TRADE_SIGNALS,
            metadata={
                "ticker": signal.get("ticker", ""),
                "direction": signal.get("direction", ""),
                "confidence": str(signal.get("confidence", 0)),
            },
        )

    async def recall_similar_setups(self, ticker: str, context: str) -> list[dict]:
        query = f"{ticker}: {context}"
        return await self.recall(query, collection=COLLECTION_TRADE_SIGNALS, n_results=3)


# Singleton
memory = SemanticMemory()
