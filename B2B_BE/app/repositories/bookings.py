from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking


async def create_booking(
    db: AsyncSession,
    *,
    customer_id: int,
    staff_id: int,
    service_name: str,
    start_time: datetime,
    status: str = "confirmed",
) -> Booking:
    """Insert a new Booking row and return it.

    This is the sole insert path for a Booking row in the codebase.
    """
    booking = Booking(
        customer_id=customer_id,
        staff_id=staff_id,
        service_name=service_name,
        start_time=start_time,
        status=status,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking
