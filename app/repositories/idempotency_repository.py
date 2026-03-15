from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency_key import IdempotencyKey


class IdempotencyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int | None,
        scope: str,
        key: str,
        status: str = "processing",
    ) -> IdempotencyKey | None:
        async with self.session.begin_nested():
            item = IdempotencyKey(user_id=user_id, scope=scope, key=key, status=status)
            self.session.add(item)
            try:
                await self.session.flush()
            except IntegrityError:
                return None
            return item

    async def get(self, scope: str, key: str) -> IdempotencyKey | None:
        result = await self.session.execute(
            select(IdempotencyKey).where(IdempotencyKey.scope == scope, IdempotencyKey.key == key)
        )
        return result.scalar_one_or_none()

    async def update_status(self, item: IdempotencyKey, status: str) -> IdempotencyKey:
        item.status = status
        await self.session.flush()
        return item
