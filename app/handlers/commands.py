from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.dependencies import AppContainer
from app.keyboards.common import buy_package_keyboard, main_menu_keyboard

router = Router()


async def send_start_message(message: Message, container: AppContainer) -> None:
    if message.from_user is None:
        return
    free_credits, paid_credits = await container.credit_service.get_balance(message.from_user.id)
    total = free_credits + paid_credits
    await message.answer(
        "Hi! I turn regular photos into photorealistic vintage flash shots.\n\n"
        f"You currently have {total} edits available "
        f"({free_credits} free, {paid_credits} paid).\n"
        "Send me a photo and I will turn it into a vintage flash-style image.",
        reply_markup=main_menu_keyboard(),
    )


async def send_help_message(message: Message, container: AppContainer) -> None:
    await message.answer(
        "How it works:\n"
        "1. Send a photo.\n"
        "2. I will process it in a vintage early-2000s flash style.\n"
        f"3. After {container.settings.free_credits_on_start} free edits, you can buy "
        f"a package of {container.settings.package_credits} photos for {container.settings.package_price_stars} Stars.\n\n"
        "Commands: /balance, /buy, /help",
        reply_markup=main_menu_keyboard(),
    )


async def send_balance_message(message: Message, container: AppContainer) -> None:
    if message.from_user is None:
        return
    free_credits, paid_credits = await container.credit_service.get_balance(message.from_user.id)
    total = free_credits + paid_credits
    await message.answer(
        "Your balance:\n"
        f"Free edits: {free_credits}\n"
        f"Paid edits: {paid_credits}\n"
        f"Total remaining: {total}",
        reply_markup=main_menu_keyboard(),
    )


async def send_buy_message(message: Message, container: AppContainer) -> None:
    await message.answer(
        f"Package: {container.settings.package_credits} photos for {container.settings.package_price_stars} Stars.\n"
        "Tap the button below to open the Telegram Stars payment screen.",
        reply_markup=buy_package_keyboard(),
    )


@router.message(Command("start"))
async def start_handler(message: Message, container: AppContainer) -> None:
    if message.from_user is None:
        return
    await container.user_service.get_or_create_user(message.from_user)
    await send_start_message(message, container)


@router.message(Command("help"))
async def help_handler(message: Message, container: AppContainer) -> None:
    if message.from_user is None:
        return
    await container.user_service.get_or_create_user(message.from_user)
    await send_help_message(message, container)


@router.message(Command("balance"))
async def balance_handler(message: Message, container: AppContainer) -> None:
    if message.from_user is None:
        return
    await container.user_service.get_or_create_user(message.from_user)
    await send_balance_message(message, container)


@router.message(Command("buy"))
async def buy_handler(message: Message, container: AppContainer) -> None:
    if message.from_user is None:
        return
    await container.user_service.get_or_create_user(message.from_user)
    await send_buy_message(message, container)


@router.message(F.text == "Help")
async def help_button_handler(message: Message, container: AppContainer) -> None:
    if message.from_user is None:
        return
    await container.user_service.get_or_create_user(message.from_user)
    await send_help_message(message, container)


@router.message(F.text == "Balance")
async def balance_button_handler(message: Message, container: AppContainer) -> None:
    if message.from_user is None:
        return
    await container.user_service.get_or_create_user(message.from_user)
    await send_balance_message(message, container)


@router.message(F.text == "Buy")
async def buy_button_handler(message: Message, container: AppContainer) -> None:
    if message.from_user is None:
        return
    await container.user_service.get_or_create_user(message.from_user)
    await send_buy_message(message, container)


@router.message(F.text == "Send Photo")
async def send_photo_hint_handler(message: Message, container: AppContainer) -> None:
    if message.from_user is None:
        return
    await container.user_service.get_or_create_user(message.from_user)
    await message.answer(
        "Send a photo in your next message and I will process it into a vintage flash-style image.",
        reply_markup=main_menu_keyboard(),
    )
