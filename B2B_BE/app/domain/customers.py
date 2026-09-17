from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.repositories.customers import create_customer, get_customer_by_phone


def find_or_create_customer(db: Session, phone_number: str, name: str) -> Customer:
    """Look up a Customer by phone number, creating one if none exists.

    If a Customer already exists for ``phone_number``, it is returned
    unchanged (``name`` is ignored in this branch — an existing customer's
    name is never overwritten). Otherwise a new Customer is created with the
    given ``phone_number`` and ``name`` and returned.

    This function is idempotent: calling it twice with the same
    ``phone_number`` never creates a duplicate Customer record.
    """
    existing = get_customer_by_phone(db, phone_number)
    if existing is not None:
        return existing
    return create_customer(db, phone_number, name)
