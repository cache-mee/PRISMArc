from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


async def get_customer_by_phone(db: AsyncSession, phone_number: str) -> Customer | None:
    """Look up a Customer by phone number, or return ``None`` if none exists."""
    result = await db.execute(
        select(Customer).where(Customer.phone_number == phone_number)
    )
    return result.scalar_one_or_none()


async def create_customer(db: AsyncSession, phone_number: str, name: str) -> Customer:
    """Insert a new Customer row and return it."""
    customer = Customer(phone_number=phone_number, name=name)
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer
