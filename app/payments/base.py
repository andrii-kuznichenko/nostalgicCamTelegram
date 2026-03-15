from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PaymentCreateResult:
    provider_payment_id: str
    payment_url: str | None
    amount_usd: Decimal
    credits: int
    title: str | None = None
    description: str | None = None
    currency: str | None = None
    amount_minor_units: int | None = None


@dataclass
class PaymentVerifyResult:
    provider_payment_id: str
    is_paid: bool
    amount_usd: Decimal
    credits_added: int


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    async def create_payment(self, telegram_user_id: int, amount_usd: Decimal, credits: int) -> PaymentCreateResult:
        raise NotImplementedError

    @abstractmethod
    async def verify_payment(self, provider_payment_id: str) -> PaymentVerifyResult:
        raise NotImplementedError

    async def close(self) -> None:
        return None
