from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        amount_usd: Decimal,
        credits_added: int,
        provider: str,
        provider_payment_id: str,
        status: str = "pending",
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            amount_usd=amount_usd,
            credits_added=credits_added,
            provider=provider,
            provider_payment_id=provider_payment_id,
            status=status,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_provider_payment_id(self, provider: str, provider_payment_id: str) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(
                Payment.provider == provider,
                Payment.provider_payment_id == provider_payment_id,
            )
        )
        return result.scalar_one_or_none()
