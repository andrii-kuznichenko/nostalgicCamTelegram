import asyncio


class UserGenerationLockRegistry:
    def __init__(self) -> None:
        self._locks: dict[int, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def get_lock(self, user_id: int) -> asyncio.Lock:
        async with self._guard:
            if user_id not in self._locks:
                self._locks[user_id] = asyncio.Lock()
            return self._locks[user_id]


lock_registry = UserGenerationLockRegistry()
