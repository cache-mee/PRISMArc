from pydantic import BaseModel

from app.database import SessionLocal
from app.domain.appointments import BookingHistory, get_booking_history


class GetBookingHistoryArgs(BaseModel):
    """Arguments for the get-booking-history tool."""

    customer_id: int


async def get_booking_history_tool(args: GetBookingHistoryArgs) -> BookingHistory:
    """Booking history (FR-10) for the future Booking Agent registry.

    Delegates to app.domain.appointments.get_booking_history, the single
    place the upcoming/past split business rule lives. Opens its own session
    via SessionLocal since this is an in-process, LLM-callable tool with no
    request-scoped session available to it — mirrors
    app.tools.customers.identify_or_create_customer_tool.

    Not yet registered into any agent's tool registry; that wiring is future,
    not-yet-built conversational-loop work.
    """
    async with SessionLocal() as db:
        return await get_booking_history(db, customer_id=args.customer_id)
