import os
from collections.abc import AsyncGenerator
from datetime import UTC

# Every unit test that exercises app.agent.manager_agent/booking_agent/catalog_intent
# constructs a real BedrockProvider even when its ``.generate()`` is mocked (see e.g.
# tests/agent/test_manager_agent.py) — BedrockProvider.__init__ always builds a real
# boto3.client("bedrock-runtime", ...), and botocore resolves an endpoint (raising
# ``NoRegionError``) at construction time, before any mocked call ever happens. A local
# dev machine's .env supplies AWS_REGION, masking this, but a bare CI runner has
# nothing set — setdefault() here (before importing app.main, which imports app.config,
# which reads AWS_REGION at module-import time) guarantees client construction always
# succeeds; the real API call is always mocked in these tests, so this value is never
# actually used to contact AWS.
os.environ.setdefault("AWS_REGION", "us-east-1")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.main import app  # noqa: E402
from app.models.availability import Availability  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.booking import Booking  # noqa: E402

# Import every model module so Base.metadata is fully populated before
# db_sessionmaker's create_all runs below - mirrors app.database's
# module-level engine, but scoped to a throwaway in-memory SQLite DB.
from app.models import availability as _availability_models  # noqa: E402,F401
from app.models import booking as _booking_models  # noqa: E402,F401
from app.models import customer as _customer_models  # noqa: E402,F401
from app.models import salon as _salon_models  # noqa: E402,F401
from app.models import service as _service_models  # noqa: E402,F401
from app.models import staff as _staff_models  # noqa: E402,F401


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _reattach_utc_if_naive(target: Availability | Booking, _context: object) -> None:
    """Re-attach UTC tzinfo to ``start_time``/``end_time`` on load, if naive.

    SQLAlchemy's sqlite dialect DATETIME type strips tzinfo on round-trip regardless of
    the column declaring ``DateTime(timezone=True)`` — unlike Postgres/psycopg, which
    correctly hands back timezone-aware datetimes for that column type. Without this,
    SQLite-backed tests silently exercise a naive/naive comparison in
    ``app.domain.availability._is_blocked_at`` that can never catch a real
    naive-vs-aware ``TypeError`` only Postgres would actually hit. A no-op for an
    already-aware value, so this can never mask a genuine tzinfo bug the other way.
    """
    for attr in ("start_time", "end_time"):
        value = getattr(target, attr, None)
        if value is not None and value.tzinfo is None:
            setattr(target, attr, value.replace(tzinfo=UTC))


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
    event.listen(Availability, "load", _reattach_utc_if_naive)
    event.listen(Booking, "load", _reattach_utc_if_naive)

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_sessionmaker(engine, expire_on_commit=False)

    await engine.dispose()
    event.remove(Availability, "load", _reattach_utc_if_naive)
    event.remove(Booking, "load", _reattach_utc_if_naive)
