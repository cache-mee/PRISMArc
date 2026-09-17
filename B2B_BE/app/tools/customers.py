from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.customers import find_or_create_customer


class IdentifyOrCreateCustomerArgs(BaseModel):
    """Arguments for the identify-or-create-customer tool."""

    phone_number: str
    name: str


class CustomerRecord(BaseModel):
    """The tool's response shape, decoupled from the ORM model."""

    id: int
    phone_number: str
    name: str


async def identify_or_create_customer_tool(
    args: IdentifyOrCreateCustomerArgs, session: AsyncSession
) -> CustomerRecord:
    """Identify an existing Customer by phone number, or create a new one.

    This is the in-process tool seam a future Booking Agent registers to
    satisfy FR-2: it validates its arguments via ``IdentifyOrCreateCustomerArgs``,
    delegates the lookup-or-create business rule to
    ``app.domain.customers.find_or_create_customer``, and maps the returned
    ``Customer`` ORM object to the decoupled ``CustomerRecord`` response shape.
    """
    customer = await find_or_create_customer(session, args.phone_number, args.name)
    return CustomerRecord(
        id=customer.id,
        phone_number=customer.phone_number,
        name=customer.name,
    )
