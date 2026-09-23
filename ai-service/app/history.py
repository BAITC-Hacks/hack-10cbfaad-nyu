import json
from collections import defaultdict
from typing import Any


class ConversationStore:
    """Redis-backed conversation storage with an in-memory fallback for tests/local MVP."""

    def __init__(self, redis_url: str = "", ttl_seconds: int = 86400):
        self.ttl_seconds = ttl_seconds
        self._local: dict[str, list[dict[str, str]]] = defaultdict(list)
        self._redis = None
        if redis_url:
            try:
                from redis.asyncio import Redis
                self._redis = Redis.from_url(redis_url, decode_responses=True)
            except ImportError:
                self._redis = None

    async def get(self, conversation_id: str) -> list[dict[str, str]]:
        if self._redis:
            raw = await self._redis.get(self._key(conversation_id))
            return json.loads(raw) if raw else []
        return list(self._local[conversation_id])

    async def append(self, conversation_id: str, *messages: dict[str, str]) -> None:
        history = await self.get(conversation_id)
        history.extend(messages)
        if self._redis:
            await self._redis.setex(self._key(conversation_id), self.ttl_seconds, json.dumps(history))
        else:
            self._local[conversation_id] = history

    def _key(self, conversation_id: str) -> str:
        return f"ai:conversation:{conversation_id}"
