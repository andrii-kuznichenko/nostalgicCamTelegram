from aiogram import F, Router
from aiogram.types import Message

from app.bot.dependencies import AppContainer
from app.keyboards.common import no_credits_keyboard

router = Router()


@router.message(F.photo)
async def photo_handler(message: Message, container: AppContainer) -> None:
    if message.from_user is None:
        return
    await container.user_service.get_or_create_user(message.from_user)
    result_message = await container.generation_service.process_photo(container.bot, message)
    if result_message:
        if "You have no edits left" in result_message:
            await message.answer(result_message, reply_markup=no_credits_keyboard())
            return
        await message.answer(result_message)


@router.message()
async def fallback_handler(message: Message, container: AppContainer) -> None:
    if message.from_user is None:
        return
    await container.user_service.get_or_create_user(message.from_user)
    await message.answer(
        "Please send a photo. If preview mode is enabled, I will return an analysis summary and the edit settings."
    )
