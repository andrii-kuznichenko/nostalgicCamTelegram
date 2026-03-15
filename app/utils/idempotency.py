from aiogram.types import Message


def build_photo_request_key(message: Message) -> str:
    return f"telegram_message:{message.chat.id}:{message.message_id}"
