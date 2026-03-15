from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def buy_package_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Buy Now", callback_data="payment:create")
    builder.adjust(1)
    return builder.as_markup()


def confirm_payment_keyboard(provider_payment_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Buy Now", callback_data="payment:create")
    builder.adjust(1)
    return builder.as_markup()


def no_credits_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Buy Package", callback_data="payment:create")
    builder.adjust(1)
    return builder.as_markup()


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Send Photo")],
            [KeyboardButton(text="Balance"), KeyboardButton(text="Buy")],
            [KeyboardButton(text="Help")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Send a photo or choose an action",
    )
