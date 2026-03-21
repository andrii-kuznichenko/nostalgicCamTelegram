from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.dependencies import AppContainer
from app.handlers.payments import build_stars_prices

router = Router()


@router.callback_query(F.data == "payment:create")
async def create_payment_callback(callback: CallbackQuery, container: AppContainer) -> None:
    if callback.from_user is None or callback.message is None:
        return

    await container.user_service.get_or_create_user(callback.from_user)
    payment = await container.payment_service.create_payment(callback.from_user.id)

    await callback.message.answer_invoice(
        title=payment.title or container.settings.package_label,
        description=payment.description or "Vintage flash photo edit package",
        payload=payment.provider_payment_id,
        currency=payment.currency or "XTR",
        prices=build_stars_prices(container),
        provider_token="",
    )
    await callback.answer("Invoice sent.")
