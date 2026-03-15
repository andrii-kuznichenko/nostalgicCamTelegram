import uuid
from pathlib import Path

from aiogram import Bot


async def download_telegram_file(bot: Bot, file_id: str, temp_dir: Path, suffix: str = ".jpg") -> Path:
    telegram_file = await bot.get_file(file_id)
    destination = temp_dir / f"source_{uuid.uuid4().hex}{suffix}"
    await bot.download_file(telegram_file.file_path, destination=destination)
    return destination
