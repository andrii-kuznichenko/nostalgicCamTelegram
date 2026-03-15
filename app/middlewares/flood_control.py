import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import Settings


class FloodControlMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._hits: dict[tuple[int, str], float] = {}
        self._guard = asyncio.Lock()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        event_type = "unknown"
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            event_type = "message"
        if isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
            event_type = "callback"

        if user_id is None:
            return await handler(event, data)

        now = asyncio.get_running_loop().time()
        async with self._guard:
            key = (user_id, event_type)
            last_hit = self._hits.get(key, 0.0)
            if now - last_hit < self.settings.flood_window_seconds:
                if isinstance(event, Message):
                    await event.answer("Too fast. Please wait a couple of seconds and try again.")
                    return None
                if isinstance(event, CallbackQuery):
                    await event.answer("Too fast. Please wait a couple of seconds.", show_alert=False)
                    return None
            self._hits[key] = now

        return await handler(event, data)
