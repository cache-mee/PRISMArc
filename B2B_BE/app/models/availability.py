from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Availability(Base):
    """A staff block/unblock window (FR-27).

    Written only via ``confirm_and_apply_availability_change`` once a
    ``ProposedAvailabilityChange`` has been explicitly confirmed — no other
    code path in the repo constructs this row.
    """

    __tablename__ = "availability"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    staff_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("staff.id"), nullable=False, index=True
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
