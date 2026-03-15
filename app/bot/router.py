from aiogram import Dispatcher

from app.handlers.callbacks import router as callbacks_router
from app.handlers.commands import router as commands_router
from app.handlers.payments import router as payments_router
from app.handlers.photos import router as photos_router


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(commands_router)
    dp.include_router(callbacks_router)
    dp.include_router(payments_router)
    dp.include_router(photos_router)
