import asyncio
from time import monotonic


class MessageDedupRegistry:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def register(self, key: str) -> bool:
        async with self._lock:
            self._cleanup_expired()
            if key in self._items:
                return False
            self._items[key] = monotonic()
            return True

    async def forget(self, key: str) -> None:
        async with self._lock:
            self._items.pop(key, None)

    def _cleanup_expired(self) -> None:
        now = monotonic()
        expired = [
            key for key, created_at in self._items.items()
            if now - created_at > self.ttl_seconds
        ]
        for key in expired:
            self._items.pop(key, None)


message_dedup_registry = MessageDedupRegistry()
