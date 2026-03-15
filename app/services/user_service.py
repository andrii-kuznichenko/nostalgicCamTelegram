from aiogram.types import User as TgUser

from app.config import Settings
from app.db.session import SessionLocal
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def get_or_create_user(self, tg_user: TgUser):
        async with SessionLocal() as session:
            repo = UserRepository(session)
            async with session.begin():
                user = await repo.get_by_telegram_user_id(tg_user.id)
                if user is None:
                    user = await repo.create(
                        telegram_user_id=tg_user.id,
                        username=tg_user.username,
                        first_name=tg_user.first_name,
                        last_name=tg_user.last_name,
                        free_credits=self.settings.free_credits_on_start,
                    )
                else:
                    await repo.update_profile(
                        user,
                        username=tg_user.username,
                        first_name=tg_user.first_name,
                        last_name=tg_user.last_name,
                    )
            return user
