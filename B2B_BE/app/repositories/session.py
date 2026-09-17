from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url)

async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` for repository functions to use.

    Usage::

        async with get_session() as session:
            ...
    """
    async with async_session_factory() as session:
        yield session
