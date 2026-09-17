"""Customer repository — the phone-lookup data-access method FR-1 needs.

Read-only for this ticket: ``get_by_phone`` is the only method added here.
``create(...)`` belongs to Story 1.3 (FR-2), which is the ticket that actually
creates a ``Customer`` record — see the APPOINTMEN-14 implementation plan,
*Technical Context*, decision 3.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer


def get_by_phone(db: Session, phone_number: str) -> Customer | None:
    """Return the ``Customer`` matching ``phone_number``, or ``None``."""
    return db.execute(
        select(Customer).where(Customer.phone_number == phone_number)
    ).scalar_one_or_none()
