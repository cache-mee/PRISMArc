from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.base import Base

# Import every model module so Base.metadata is fully populated before
# db_sessionmaker's create_all runs below - mirrors app.database's
# module-level engine, but scoped to a throwaway in-memory SQLite DB.
from app.models import availability as _availability_models  # noqa: F401
from app.models import booking as _booking_models  # noqa: F401
from app.models import customer as _customer_models  # noqa: F401
from app.models import salon as _salon_models  # noqa: F401
from app.models import service as _service_models  # noqa: F401
from app.models import staff as _staff_models  # noqa: F401


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
async def db_sessionmaker() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """A fresh, in-memory SQLite async engine/sessionmaker for one test (FR-31).

    APPOINTMEN-46's regression coverage needs a real ``AsyncSession`` against
    a real backing store to exercise SQLAlchemy's own session/identity-map
    behavior — a mocked session cannot demonstrate that. SQLite via
    ``aiosqlite`` (a dev-only test dependency, never the Postgres+psycopg
    driver ``app.database`` uses at runtime) keeps this fast and
    self-contained. ``StaticPool`` shares one underlying connection across
    every session this fixture's sessionmaker creates — otherwise each
    ``:memory:`` SQLite connection would be its own empty database, and nothing
    written by one test session would ever be visible to another, unlike the
    single shared Postgres database every real request/session talks to.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_sessionmaker(engine, expire_on_commit=False)

    await engine.dispose()
