import logging
from decimal import Decimal

from sqlalchemy import select

from app.config import Settings
from app.db.session import SessionLocal
from app.models.user import User
from app.payments.base import PaymentCreateResult, PaymentProvider, PaymentVerifyResult
from app.repositories.payment_repository import PaymentRepository

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, settings: Settings, provider: PaymentProvider):
        self.settings = settings
        self.provider = provider

    async def create_payment(self, telegram_user_id: int) -> PaymentCreateResult:
        payment_result = await self.provider.create_payment(
            telegram_user_id=telegram_user_id,
            amount_usd=Decimal(str(self.settings.package_price_usd)),
            credits=self.settings.package_credits,
        )
        async with SessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    select(User).where(User.telegram_user_id == telegram_user_id)
                )
                user = result.scalar_one()
                repo = PaymentRepository(session)
                existing = await repo.get_by_provider_payment_id(
                    self.provider.name,
                    payment_result.provider_payment_id,
                )
                if existing is None:
                    await repo.create(
                        user_id=user.id,
                        amount_usd=payment_result.amount_usd,
                        credits_added=payment_result.credits,
                        provider=self.provider.name,
                        provider_payment_id=payment_result.provider_payment_id,
                        status="pending",
                    )
        return payment_result

    async def has_pending_payment(self, provider_payment_id: str) -> bool:
        async with SessionLocal() as session:
            repo = PaymentRepository(session)
            payment = await repo.get_by_provider_payment_id(self.provider.name, provider_payment_id)
            return payment is not None and payment.status == "pending"

    async def apply_successful_stars_payment(
        self,
        telegram_user_id: int,
        invoice_payload: str,
        telegram_payment_charge_id: str,
    ) -> bool:
        async with SessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    select(User).where(User.telegram_user_id == telegram_user_id).with_for_update()
                )
                user = result.scalar_one()

                repo = PaymentRepository(session)
                paid_payment = await repo.get_by_provider_payment_id(
                    self.provider.name,
                    telegram_payment_charge_id,
                )
                if paid_payment and paid_payment.status == "paid":
                    logger.info("Stars payment already applied: %s", telegram_payment_charge_id)
                    return True

                pending_payment = await repo.get_by_provider_payment_id(
                    self.provider.name,
                    invoice_payload,
                )
                if pending_payment is None:
                    logger.warning("Pending stars payment not found for payload: %s", invoice_payload)
                    return False

                pending_payment.provider_payment_id = telegram_payment_charge_id
                pending_payment.status = "paid"
                user.paid_credits += pending_payment.credits_added
                await session.flush()
                logger.info(
                    "Stars payment applied: charge=%s payload=%s user=%s credits=%s",
                    telegram_payment_charge_id,
                    invoice_payload,
                    telegram_user_id,
                    pending_payment.credits_added,
                )
                return True
