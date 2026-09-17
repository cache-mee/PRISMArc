from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.repositories.customers import create_customer, get_customer_by_phone


async def find_or_create_customer(
    session: AsyncSession, phone_number: str, name: str
) -> Customer:
    """Look up a Customer by phone number, creating one if none exists.

    If a Customer already exists for ``phone_number``, it is returned
    unchanged (``name`` is ignored in this branch — an existing customer's
    name is never overwritten). Otherwise a new Customer is created with the
    given ``phone_number`` and ``name`` and returned.

    This function is idempotent: calling it twice with the same
    ``phone_number`` never creates a duplicate Customer record.
    """
    existing = await get_customer_by_phone(session, phone_number)
    if existing is not None:
        return existing
    return await create_customer(session, phone_number, name)
