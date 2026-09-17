from pydantic import BaseModel

from app.database import SessionLocal
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


def identify_or_create_customer_tool(args: IdentifyOrCreateCustomerArgs) -> CustomerRecord:
    """Identify an existing Customer by phone number, or create a new one.

    This is the in-process tool seam a future Booking Agent registers to
    satisfy FR-2: it validates its arguments via ``IdentifyOrCreateCustomerArgs``,
    delegates the lookup-or-create business rule to
    ``app.domain.customers.find_or_create_customer``, and maps the returned
    ``Customer`` ORM object to the decoupled ``CustomerRecord`` response shape.

    Opens its own session via SessionLocal since this is an in-process,
    LLM-callable tool with no request-scoped session available to it.
    """
    db = SessionLocal()
    try:
        customer = find_or_create_customer(db, args.phone_number, args.name)
        return CustomerRecord(
            id=customer.id,
            phone_number=customer.phone_number,
            name=customer.name,
        )
    finally:
        db.close()
