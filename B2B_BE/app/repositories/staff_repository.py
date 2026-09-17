from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import Staff, StaffRole


async def list_bookable_staff(db: AsyncSession) -> list[Staff]:
    """Staff a Customer can book — excludes the Owner/Admin (AC3).

    Ordered by name (mirrors ``app.repositories.services.list_services``'s
    shape) — used by FR-8's ``find_nearest_alternatives``
    (app.domain.appointments) as the salon-wide candidate-staff set when the
    Customer stated no staff preference.
    """
    result = await db.execute(
        select(Staff).where(Staff.role != StaffRole.OWNER_ADMIN).order_by(Staff.name)
    )
    return list(result.scalars().all())


async def list_dashboard_staff(db: AsyncSession) -> list[Staff]:
    """Staff shown on the Dashboard's staff list — excludes the Owner/Admin (AC3)."""
    result = await db.execute(select(Staff).where(Staff.role != StaffRole.OWNER_ADMIN))
    return list(result.scalars().all())


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
