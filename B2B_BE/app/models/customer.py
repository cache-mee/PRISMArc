"""Customer model.

The one Epic-1 entity FR-1 (APPOINTMEN-14) needs: a phone-number-keyed
record used to resolve a returning Web Chat customer. The rest of Story
1.1's data model (``staff``, ``services``, ``bookings``, ``availability``)
is intentionally not modeled here — see the APPOINTMEN-14 implementation
plan, *Technical Context*.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Customer(Base):
    """A known customer, identified by phone number."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
