import logging
import contextlib
import asyncio
from pathlib import Path

from aiogram import Bot
from aiogram.enums import ChatAction
from aiogram.types import FSInputFile, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, VINTAGE_FLASH_PROMPT
from app.db.session import SessionLocal
from app.models.user import User
from app.repositories.generation_repository import GenerationRepository
from app.services.ai.base import AIImageEditingService, AIServiceError
from app.services.credit_service import CreditService
from app.services.generation_locks import lock_registry
from app.services.image_analysis import ImageAnalyzer
from app.services.message_dedup import message_dedup_registry
from app.services.prompt_builder import PromptBuilder
from app.services.prompt_preview_formatter import build_preview_messages
from app.utils.files import download_telegram_file
from app.utils.idempotency import build_photo_request_key

logger = logging.getLogger(__name__)


class GenerationService:
    def __init__(
        self,
        settings: Settings,
        ai_service: AIImageEditingService,
        credit_service: CreditService,
        image_analyzer: ImageAnalyzer,
        prompt_builder: PromptBuilder,
    ) -> None:
        self.settings = settings
        self.ai_service = ai_service
        self.credit_service = credit_service
        self.image_analyzer = image_analyzer
        self.prompt_builder = prompt_builder

    async def _run_chat_action_loop(self, bot: Bot, chat_id: int, action: ChatAction) -> None:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action=action)
            await asyncio.sleep(4)

    async def process_photo(self, bot: Bot, message: Message) -> str:
        tg_user = message.from_user
        if tg_user is None or not message.photo:
            raise ValueError("Message does not contain photo")

        lock = await lock_registry.get_lock(tg_user.id)
        if lock.locked():
            return "Your previous photo is still being processed. Please wait for the result before sending another one."

        async with lock:
            photo = message.photo[-1]
            if photo.file_size and photo.file_size > self.settings.max_photo_size_bytes:
                return "The photo is too large. Please send an image up to 10 MB."

            request_key = build_photo_request_key(message)
            is_new_message = await message_dedup_registry.register(request_key)
            if not is_new_message:
                logger.info("Duplicate photo request ignored: %s", request_key)
                return "This photo message is already being processed or has already been handled. Please send a new photo."

            user_db_id: int | None = None
            async with SessionLocal() as session:
                async with session.begin():
                    result = await session.execute(
                        select(User).where(User.telegram_user_id == tg_user.id)
                    )
                    user = result.scalar_one()
                    user_db_id = user.id
                    if not self.settings.prompt_preview_mode and user.free_credits + user.paid_credits <= 0:
                        await message_dedup_registry.forget(request_key)
                        return (
                            f"You have no edits left. You can buy a package of "
                            f"{self.settings.package_credits} photos for {self.settings.package_price_stars} Stars with /buy."
                        )

            try:
                source_path = await download_telegram_file(
                    bot=bot,
                    file_id=photo.file_id,
                    temp_dir=self.settings.temp_dir,
                    suffix=".jpg",
                )
            except Exception:
                logger.exception("Failed to download Telegram file")
                await message_dedup_registry.forget(request_key)
                return "Failed to download the photo. Please try sending it again."

            async with SessionLocal() as session:
                async with session.begin():
                    generation_repo = GenerationRepository(session)
                    generation = await generation_repo.create(
                        user_id=user_db_id,
                        source_file_path=str(source_path),
                        prompt_used=VINTAGE_FLASH_PROMPT,
                        status="processing",
                    )

                if self.settings.prompt_preview_mode:
                    return await self._run_prompt_preview(
                        session=session,
                        generation_repo=generation_repo,
                        generation=generation,
                        source_path=source_path,
                        message=message,
                        request_key=request_key,
                    )

                return await self._run_generation(
                    bot=bot,
                    session=session,
                    generation_repo=generation_repo,
                    generation=generation,
                    source_path=source_path,
                    message=message,
                    request_key=request_key,
                )

    async def _run_prompt_preview(
        self,
        *,
        session: AsyncSession,
        generation_repo: GenerationRepository,
        generation,
        source_path: Path,
        message: Message,
        request_key: str,
    ) -> str:
        try:
            analysis = await self.image_analyzer.analyze(source_path)
            prompt_package = self.prompt_builder.build_flux_prompt(analysis)
            logger.info(
                "Prompt preview built: user=%s photo_type=%s mode=%s",
                message.from_user.id if message.from_user else "unknown",
                analysis.photo_type,
                prompt_package.selected_mode,
            )
        except Exception as exc:
            logger.exception("Prompt preview analysis failed")
            async with session.begin():
                await generation_repo.mark_failed(generation, f"prompt_preview_failed: {exc}")
            await message_dedup_registry.forget(request_key)
            return "Could not analyze the photo and build the prompt. Please try again."

        try:
            for chunk in build_preview_messages(analysis, prompt_package):
                await message.answer(chunk)
        except Exception:
            logger.exception("Failed to send prompt preview messages")
            async with session.begin():
                await generation_repo.mark_failed(generation, "send_preview_failed")
            await message_dedup_registry.forget(request_key)
            return "Failed to send the analysis result. Please try again."

        async with session.begin():
            generation.prompt_used = prompt_package.prompt
            generation.status = "previewed"
            generation.result_file_path = None
            generation.error_message = prompt_package.negative_prompt
            await session.flush()

        await message_dedup_registry.forget(request_key)
        return ""

    async def _run_generation(
        self,
        *,
        bot: Bot,
        session: AsyncSession,
        generation_repo: GenerationRepository,
        generation,
        source_path: Path,
        message: Message,
        request_key: str,
    ) -> str:
        progress_message = await message.answer("Starting your edit...")
        last_progress_text = progress_message.text or ""

        async def progress_callback(text: str) -> None:
            nonlocal last_progress_text
            if text == last_progress_text:
                return
            last_progress_text = text
            with contextlib.suppress(Exception):
                await progress_message.edit_text(text)

        action_task = asyncio.create_task(
            self._run_chat_action_loop(bot=bot, chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
        )

        try:
            result_path = await self.ai_service.edit_image(
                image_path=source_path,
                prompt=VINTAGE_FLASH_PROMPT,
                progress_callback=progress_callback,
            )
        except AIServiceError as exc:
            action_task.cancel()
            with contextlib.suppress(Exception):
                await progress_message.edit_text("Editing failed. Please try again.")
            logger.exception("Image edit provider failed: %s", exc)
            async with session.begin():
                await generation_repo.mark_failed(generation, str(exc))
            await message_dedup_registry.forget(request_key)
            return "Could not process the photo. Please try again."

        try:
            with contextlib.suppress(Exception):
                await progress_message.edit_text("Sending your result...")
            await message.answer_photo(
                photo=FSInputFile(result_path),
                caption="Done. Here is your processed photo.",
            )
        except Exception:
            action_task.cancel()
            with contextlib.suppress(Exception):
                await progress_message.edit_text("The edit is ready, but sending the result failed.")
            logger.exception("Failed to send result photo to user")
            async with session.begin():
                await generation_repo.mark_failed(generation, "send_result_failed")
            await message_dedup_registry.forget(request_key)
            return "Failed to send the result. Please try again a bit later."

        try:
            await self.credit_service.consume_one_credit(message.from_user.id)
        except ValueError:
            async with session.begin():
                await generation_repo.mark_failed(generation, "credits_race_condition")
            await message_dedup_registry.forget(request_key)
            return "Your balance seems to have changed during processing. Please check /balance."

        async with session.begin():
            await generation_repo.mark_success(generation, str(result_path))

        action_task.cancel()
        with contextlib.suppress(Exception):
            await progress_message.edit_text("Your photo is ready.")
        logger.info("Photo processed successfully for user %s", message.from_user.id)
        return ""
