from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User


class CreditService:
    async def get_balance(self, telegram_user_id: int) -> tuple[int, int]:
        async with SessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_user_id == telegram_user_id)
            )
            user = result.scalar_one()
            return user.free_credits, user.paid_credits

    async def has_available_credit(self, telegram_user_id: int) -> bool:
        free_credits, paid_credits = await self.get_balance(telegram_user_id)
        return free_credits + paid_credits > 0

    async def consume_one_credit(self, telegram_user_id: int) -> tuple[int, int]:
        async with SessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    select(User).where(User.telegram_user_id == telegram_user_id).with_for_update()
                )
                user = result.scalar_one()
                if user.free_credits > 0:
                    user.free_credits -= 1
                elif user.paid_credits > 0:
                    user.paid_credits -= 1
                else:
                    raise ValueError("No credits available")
                await session.flush()
                return user.free_credits, user.paid_credits

    async def add_paid_credits(self, telegram_user_id: int, credits: int) -> tuple[int, int]:
        async with SessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    select(User).where(User.telegram_user_id == telegram_user_id).with_for_update()
                )
                user = result.scalar_one()
                user.paid_credits += credits
                await session.flush()
                return user.free_credits, user.paid_credits
