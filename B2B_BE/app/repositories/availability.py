from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.availability import Availability


async def create_availability(
    db: AsyncSession,
    *,
    staff_id: int,
    start_time: datetime,
    end_time: datetime,
    blocked: bool,
) -> Availability:
    """Insert a new Availability row and return it.

    This is the sole insert path for an Availability row in the codebase.
    """
    availability = Availability(
        staff_id=staff_id,
        start_time=start_time,
        end_time=end_time,
        blocked=blocked,
    )
    db.add(availability)
    await db.commit()
    await db.refresh(availability)
    return availability
