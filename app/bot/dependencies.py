from dataclasses import dataclass

from aiogram import Bot

from app.config import Settings, get_settings
from app.payments.base import PaymentProvider
from app.payments.telegram_stars import TelegramStarsPaymentProvider
from app.services.ai.base import AIImageEditingService
from app.services.ai.fal_flux_provider import FalFluxImageEditingService
from app.services.ai.http_provider import HttpAIImageEditingService
from app.services.ai.mock_provider import MockAIImageEditingService
from app.services.credit_service import CreditService
from app.services.generation_service import GenerationService
from app.services.image_analysis import HeuristicImageAnalyzer, ImageAnalyzer
from app.services.payment_service import PaymentService
from app.services.prompt_builder import PromptBuilder
from app.services.user_service import UserService


@dataclass
class AppContainer:
    settings: Settings
    bot: Bot
    ai_service: AIImageEditingService
    payment_provider: PaymentProvider
    image_analyzer: ImageAnalyzer
    prompt_builder: PromptBuilder
    user_service: UserService
    credit_service: CreditService
    payment_service: PaymentService
    generation_service: GenerationService

    async def close(self) -> None:
        await self.ai_service.close()
        await self.payment_provider.close()
        await self.bot.session.close()


def build_container(bot: Bot) -> AppContainer:
    settings = get_settings()
    ai_service: AIImageEditingService
    if settings.use_mock_ai_provider:
        ai_service = MockAIImageEditingService(settings)
    elif settings.ai_model_name.startswith("fal-ai/"):
        ai_service = FalFluxImageEditingService(settings)
    else:
        ai_service = HttpAIImageEditingService(settings)

    payment_provider: PaymentProvider = TelegramStarsPaymentProvider(settings)
    image_analyzer: ImageAnalyzer = HeuristicImageAnalyzer()
    prompt_builder = PromptBuilder()
    user_service = UserService(settings)
    credit_service = CreditService()
    payment_service = PaymentService(settings, payment_provider)
    generation_service = GenerationService(
        settings=settings,
        ai_service=ai_service,
        credit_service=credit_service,
        image_analyzer=image_analyzer,
        prompt_builder=prompt_builder,
    )

    return AppContainer(
        settings=settings,
        bot=bot,
        ai_service=ai_service,
        payment_provider=payment_provider,
        image_analyzer=image_analyzer,
        prompt_builder=prompt_builder,
        user_service=user_service,
        credit_service=credit_service,
        payment_service=payment_service,
        generation_service=generation_service,
    )
