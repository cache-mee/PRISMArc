"""Async SQLAlchemy engine/session wiring.

Per `base-rules.md`'s async-I/O rule: every request/tool-call-path DB access
goes through ``get_db()`` (FastAPI) or ``SessionLocal()`` (in-process tools),
both yielding an ``AsyncSession``. Models' shared declarative ``Base`` lives
in ``app.models.base`` (not here), so it stays the one metadata registry
Alembic's ``env.py`` tracks — Alembic itself still migrates synchronously,
which is unaffected by the app's runtime engine being async.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# `create_async_engine` only parses the URL eagerly; it does not connect
# until a session is actually used. Falling back to a dialect-only URL (no
# host/credentials) when `DATABASE_URL` is unset keeps this module importable
# without a live DB configured, while still failing loudly the moment a
# session actually tries to connect. psycopg 3 (already the only installed
# driver) supports SQLAlchemy's async engine natively via `+psycopg`.
engine = create_async_engine(settings.database_url or "postgresql+psycopg://")

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a request-scoped async DB session."""
    async with SessionLocal() as db:
        yield db
