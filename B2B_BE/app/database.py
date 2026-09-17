"""SQLAlchemy engine/session wiring.

Every request-scoped DB access goes through ``get_db()``. Models' shared
declarative ``Base`` lives in ``app.models.base`` (not here), so it stays the
one metadata registry Alembic's ``env.py`` tracks.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# `create_engine` only parses the URL eagerly; it does not connect until a
# session is actually used. Falling back to a dialect-only URL (no host/
# credentials) when `DATABASE_URL` is unset keeps this module importable
# without a live DB configured, while still failing loudly the moment a
# session actually tries to connect.
engine = create_engine(settings.database_url or "postgresql+psycopg://")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
