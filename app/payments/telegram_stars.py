import uuid
from decimal import Decimal

from app.config import Settings
from app.payments.base import PaymentCreateResult, PaymentProvider, PaymentVerifyResult


class TelegramStarsPaymentProvider(PaymentProvider):
    name = "telegram_stars"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_payment(self, telegram_user_id: int, amount_usd: Decimal, credits: int) -> PaymentCreateResult:
        payload = f"stars_{telegram_user_id}_{uuid.uuid4().hex}"
        return PaymentCreateResult(
            provider_payment_id=payload,
            payment_url=None,
            amount_usd=amount_usd,
            credits=credits,
            title=self.settings.package_label,
            description="Vintage flash photo edit package",
            currency="XTR",
            amount_minor_units=self.settings.package_price_stars,
        )

    async def verify_payment(self, provider_payment_id: str) -> PaymentVerifyResult:
        return PaymentVerifyResult(
            provider_payment_id=provider_payment_id,
            is_paid=False,
            amount_usd=Decimal(str(self.settings.package_price_usd)),
            credits_added=self.settings.package_credits,
        )
