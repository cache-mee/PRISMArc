from pydantic import BaseModel

from app.database import SessionLocal
from app.models.staff import StaffRole
from app.repositories.staff_repository import get_staff_by_phone_number


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
