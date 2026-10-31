import json
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    json_serializer=lambda obj: json.dumps(obj, default=str),
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
