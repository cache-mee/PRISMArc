"""Domain-layer customer identity resolution.

Thin, channel-agnostic wrapper over the repository layer — mirrors the
``domain/`` -> ``repositories/`` layering convention already fixed by
`stack/rules/base-rules.md` (e.g. `conflicts.py`'s intended shape), so the
agent module never queries the repository or the DB directly. Reusable
unchanged by the WhatsApp channel-aware resolution story (FR-3 / Story 7.1,
out of scope here) — the resolution logic itself never forks per channel.
"""

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.repositories.customers import get_customer_by_phone


def resolve_customer_by_phone(db: Session, phone_number: str) -> Customer | None:
    """Return the ``Customer`` matching ``phone_number``, or ``None``."""
    return get_customer_by_phone(db, phone_number)
