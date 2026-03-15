from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.base import Base

settings = get_settings()
engine_kwargs = {
    "future": True,
    "echo": False,
}

if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"timeout": 30}

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


async def init_db() -> None:
    import app.models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
