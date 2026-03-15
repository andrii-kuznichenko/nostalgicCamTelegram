from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_user_id(self, telegram_user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        free_credits: int,
    ) -> User:
        user = User(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            free_credits=free_credits,
            paid_credits=0,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_profile(
        self,
        user: User,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> User:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        await self.session.flush()
        return user
