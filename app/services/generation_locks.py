import asyncio
from contextlib import asynccontextmanager


class UserGenerationLockRegistry:
    def __init__(self) -> None:
        self._locks: dict[int, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def get_lock(self, user_id: int) -> asyncio.Lock:
        async with self._guard:
            if user_id not in self._locks:
                self._locks[user_id] = asyncio.Lock()
            return self._locks[user_id]


class GlobalGenerationLimiter:
    def __init__(self, limit: int) -> None:
        self._limit = max(1, limit)
        self._semaphore = asyncio.Semaphore(self._limit)
        self._guard = asyncio.Lock()
        self._active = 0
        self._waiting = 0

    @property
    def limit(self) -> int:
        return self._limit

    @asynccontextmanager
    async def acquire(self):
        async with self._guard:
            waiting_before = self._waiting
            self._waiting += 1

        await self._semaphore.acquire()
        async with self._guard:
            self._waiting -= 1
            self._active += 1

        try:
            yield waiting_before
        finally:
            async with self._guard:
                self._active = max(0, self._active - 1)
            self._semaphore.release()


lock_registry = UserGenerationLockRegistry()
generation_limiter: GlobalGenerationLimiter | None = None
