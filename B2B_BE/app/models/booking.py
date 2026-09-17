from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Booking(Base):
    """A confirmed appointment booking.

    ``service_id`` (APPOINTMEN-13) is nullable and additive: existing rows
    are backfilled by matching ``service_name`` against ``services.name``
    where possible, but an unmatched historical row keeps ``service_id`` as
    NULL rather than a guessed value. ``service_name`` itself is left in
    place — ``app.repositories.bookings.create_booking`` is the sole insert
    path for this table and still writes it — replacing it is a separate,
    larger refactor out of this ticket's scope.
    """

    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    staff_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("staff.id"), nullable=False
    )
    service_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("services.id"), nullable=True
    )
    service_name: Mapped[str] = mapped_column(String, nullable=False)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="confirmed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
