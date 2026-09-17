from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import Staff


async def get_staff_by_phone_number(
    db: AsyncSession, phone_number: str
) -> Staff | None:
    """Look up a Staff record by its exact, unique phone number."""
    result = await db.execute(select(Staff).where(Staff.phone_number == phone_number))
    return result.scalar_one_or_none()


async def get_staff_by_name(db: AsyncSession, name: str) -> Staff | None:
    """Look up a Staff record by its exact name.

    Mirrors ``get_staff_by_phone_number``. ``name`` is not guaranteed unique
    at the schema level (no unique constraint on ``staff.name``); this
    returns the first match, which is sufficient for this ticket's narrow
    scope of resolving ``ResolvedBookingCandidate.staff_name`` to a
    ``staff_id``.
    """
    result = await db.execute(select(Staff).where(Staff.name == name).limit(1))
    return result.scalar_one_or_none()
