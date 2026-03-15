import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.bot.dependencies import build_container
from app.bot.router import setup_routers
from app.config import get_settings
from app.db.session import init_db
from app.middlewares.dependencies import DependencyMiddleware
from app.middlewares.flood_control import FloodControlMiddleware
from app.services.cleanup_service import temp_cleanup_loop


async def setup_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="help", description="How to use the bot"),
            BotCommand(command="balance", description="Check your balance"),
            BotCommand(command="buy", description="Buy a package"),
        ]
    )


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    await init_db()

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    container = build_container(bot)
    setup_routers(dp)
    await setup_bot_commands(bot)

    dp.message.middleware(FloodControlMiddleware(container.settings))
    dp.callback_query.middleware(FloodControlMiddleware(container.settings))
    dp.message.middleware(DependencyMiddleware(container))
    dp.callback_query.middleware(DependencyMiddleware(container))

    cleanup_task = asyncio.create_task(temp_cleanup_loop(container.settings))

    try:
        await dp.start_polling(bot)
    finally:
        cleanup_task.cancel()
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
