from aiogram import F, Router
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery

from app.bot.dependencies import AppContainer

router = Router()


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery, container: AppContainer) -> None:
    is_known_payment = await container.payment_service.has_pending_payment(pre_checkout_query.invoice_payload)
    if not is_known_payment:
        await pre_checkout_query.answer(ok=False, error_message="Payment session expired. Please try again.")
        return
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, container: AppContainer) -> None:
    if message.from_user is None or message.successful_payment is None:
        return

    payment = message.successful_payment
    success = await container.payment_service.apply_successful_stars_payment(
        telegram_user_id=message.from_user.id,
        invoice_payload=payment.invoice_payload,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
    )
    if not success:
        await message.answer("Payment was received, but credits could not be applied automatically. Please contact support.")
        return

    free_credits, paid_credits = await container.credit_service.get_balance(message.from_user.id)
    await message.answer(
        "Payment successful. Credits have been added.\n"
        f"Free edits: {free_credits}\n"
        f"Paid edits: {paid_credits}"
    )


def build_stars_prices(container: AppContainer) -> list[LabeledPrice]:
    return [
        LabeledPrice(
            label=f"{container.settings.package_credits} photo edits",
            amount=container.settings.package_price_stars,
        )
    ]
