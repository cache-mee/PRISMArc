"""SQLAlchemy engine/session wiring.

This is the DB-session layer APPOINTMEN-12 deliberately deferred (that ticket
only proved the Alembic migration path works). Every model inherits from
``Base`` here, and every request-scoped DB access goes through ``get_db()``.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# `create_engine` only parses the URL eagerly; it does not connect until a
# session is actually used. Falling back to a dialect-only URL (no host/
# credentials) when `DATABASE_URL` is unset keeps this module importable
# without a live DB configured (e.g. structural checks), while still failing
# loudly the moment a session actually tries to connect.
engine = create_engine(settings.database_url or "postgresql+psycopg://")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base every SQLAlchemy model inherits from."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
