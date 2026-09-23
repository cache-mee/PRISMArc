from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models.staff import StaffRole
from app.repositories.staff_repository import (
    get_staff_by_phone_number,
    list_bookable_staff,
)


class ResolveStaffIdentityInput(BaseModel):
    """LLM-callable tool arguments for resolving a Staff member's identity."""

    phone_number: str


class StaffIdentity(BaseModel):
    """Resolved Staff identity returned by the tool."""

    id: int
    name: str
    role: StaffRole


async def resolve_staff_identity(phone_number: str) -> StaffIdentity | None:
    """Resolve a phone number to a Staff identity, or None if no match.

    Opens its own session via SessionLocal since this is an in-process,
    LLM-callable tool with no request-scoped session available to it.
    """
    async with SessionLocal() as db:
        staff = await get_staff_by_phone_number(db, phone_number)
        if staff is None:
            return None
        return StaffIdentity(id=staff.id, name=staff.name, role=staff.role)


async def list_bookable_staff_names(session: AsyncSession) -> list[str]:
    """Tool for the Booking Agent: names of staff who can be booked (FR-13).

    Reads through app.repositories.staff_repository — never queries the DB
    directly — so the LLM tool-calling layer stays out of the data-access
    path. Mirrors app.tools.services.get_service_catalog's shape.
    """
    staff = await list_bookable_staff(session)
    return [s.name for s in staff]
