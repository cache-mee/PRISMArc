from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.appointments import BookingHistory, get_booking_history
from app.domain.identity import resolve_customer_by_phone

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("/history", response_model=BookingHistory)
async def get_history(
    phone_number: str,
    session: AsyncSession = Depends(get_db),
) -> BookingHistory:
    """FR-10: the requesting Customer's own booking history, split into
    upcoming/past.

    Resolves the requesting Customer via
    app.domain.identity.resolve_customer_by_phone — the app's one identity
    mechanism, the same one app.agent.booking_agent already uses for the
    chat identity gate — and returns 404 if no Customer matches. No new
    identity mechanism is introduced.
    """
    customer = await resolve_customer_by_phone(session, phone_number)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return await get_booking_history(session, customer_id=customer.id)
