from datetime import UTC, datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.availability import is_staff_blocked_now
from app.models.staff import StaffRole
from app.repositories.bookings import (
    list_bookings_with_names_in_window,
    list_confirmed_bookings_for_staff_on_day,
)
from app.repositories.staff_repository import list_dashboard_staff

DashboardView = Literal["today", "week"]


class DashboardStaffStatus(BaseModel):
    """FR-19's Dashboard staff-list card: one row per staff member.

    ``staff_id``/``role`` are carried alongside the live status fields so this
    single endpoint covers both the roster (APPOINTMEN-56) and live-status
    (APPOINTMEN-47) needs of the same card, rather than shipping two
    overlapping ``/dashboard/staff`` shapes.
    """

    staff_id: int
    staff_name: str
    role: StaffRole
    blocked: bool
    today_booking_count: int


class DashboardBookingEntry(BaseModel):
    """FR-20's Dashboard bookings-view row: one confirmed appointment."""

    staff_name: str
    customer_name: str
    service_name: str
    start_time: datetime


async def get_dashboard_staff_status(db: AsyncSession) -> list[DashboardStaffStatus]:
    """Current status of every Dashboard-visible staff member (FR-19).

    For each ``list_dashboard_staff`` row (excludes Owner/Admin, AC3),
    resolves ``blocked`` via the existing ``is_staff_blocked_now`` (the same
    rule FR-7's slot search uses, so the two can never disagree) and
    ``today_booking_count`` via the existing
    ``list_confirmed_bookings_for_staff_on_day`` for today's date (UTC).
    """
    today = datetime.now(UTC).date()
    staff_rows = await list_dashboard_staff(db)

    statuses: list[DashboardStaffStatus] = []
    for staff in staff_rows:
        blocked = await is_staff_blocked_now(db, staff_id=staff.id)
        todays_bookings = await list_confirmed_bookings_for_staff_on_day(
            db, staff_id=staff.id, day=today
        )
        statuses.append(
            DashboardStaffStatus(
                staff_id=staff.id,
                staff_name=staff.name,
                role=staff.role,
                blocked=blocked,
                today_booking_count=len(todays_bookings),
            )
        )
    return statuses


def _window_for_view(
    view: DashboardView, *, now: datetime
) -> tuple[datetime, datetime]:
    """Resolve the [window_start, window_end) pair for a Dashboard bookings view.

    ``"today"`` is midnight-to-midnight UTC, matching the existing
    ``datetime.now(UTC)`` convention used by
    ``app.domain.appointments.get_booking_history``. ``"week"`` is the
    Monday-to-Sunday window containing ``now`` (``date.weekday()``: Monday is
    0), inclusive of both endpoints' calendar days.
    """
    today = now.date()
    if view == "today":
        window_start = datetime.combine(today, time.min, tzinfo=UTC)
        window_end = window_start + timedelta(days=1)
        return window_start, window_end

    monday = today - timedelta(days=today.weekday())
    window_start = datetime.combine(monday, time.min, tzinfo=UTC)
    window_end = window_start + timedelta(days=7)
    return window_start, window_end


async def get_dashboard_bookings(
    db: AsyncSession, view: DashboardView
) -> list[DashboardBookingEntry]:
    """Flat, chronological list of confirmed bookings for the requested view (FR-20).

    Computes the view's ``[window_start, window_end)`` pair (today or the
    current Monday-Sunday week) and maps
    ``list_bookings_with_names_in_window``'s joined rows to
    ``DashboardBookingEntry``. Returns rows in the query's own start_time
    order — grouping into a by-day/by-staff layout is presentation, left to
    the frontend.
    """
    window_start, window_end = _window_for_view(view, now=datetime.now(UTC))
    rows = await list_bookings_with_names_in_window(
        db, window_start=window_start, window_end=window_end
    )
    return [
        DashboardBookingEntry(
            staff_name=staff_name,
            customer_name=customer_name,
            service_name=booking.service_name,
            start_time=booking.start_time,
        )
        for booking, staff_name, customer_name in rows
    ]
