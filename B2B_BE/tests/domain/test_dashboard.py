"""Unit tests for app.domain.dashboard (APPOINTMEN-58, FR-20's AC1).

``_window_for_view``'s today/week boundary math and
``get_dashboard_bookings``'s row-mapping are tested directly, with the
repository call monkeypatched — no live DB required for this file. Mirrors
``tests/domain/test_availability.py``'s pattern of directly testing an
underscore-prefixed pure function.
"""

from datetime import UTC, datetime

import pytest

from app.domain import dashboard as dashboard_domain
from app.domain.dashboard import DashboardBookingEntry, _window_for_view, get_dashboard_bookings
from app.models.booking import Booking


def test_window_for_view_today_is_midnight_to_midnight_utc() -> None:
    now = datetime(2026, 9, 17, 14, 30, tzinfo=UTC)  # Thursday

    window_start, window_end = _window_for_view("today", now=now)

    assert window_start == datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
    assert window_end == datetime(2026, 9, 18, 0, 0, tzinfo=UTC)


def test_window_for_view_week_is_monday_to_next_monday_for_mid_week_now() -> None:
    now = datetime(2026, 9, 17, 14, 30, tzinfo=UTC)  # Thursday, 2026-09-17

    window_start, window_end = _window_for_view("week", now=now)

    assert window_start == datetime(2026, 9, 14, 0, 0, tzinfo=UTC)  # Monday
    assert window_end == datetime(2026, 9, 21, 0, 0, tzinfo=UTC)  # following Monday


def test_window_for_view_week_boundary_when_now_is_exactly_monday_midnight() -> None:
    now = datetime(2026, 9, 14, 0, 0, tzinfo=UTC)  # Monday, exactly midnight

    window_start, window_end = _window_for_view("week", now=now)

    assert window_start == now
    assert window_end == datetime(2026, 9, 21, 0, 0, tzinfo=UTC)


def test_window_for_view_week_boundary_when_now_is_sunday_just_before_midnight() -> None:
    now = datetime(2026, 9, 20, 23, 59, 59, tzinfo=UTC)  # Sunday, last instant of the week

    window_start, window_end = _window_for_view("week", now=now)

    assert window_start == datetime(2026, 9, 14, 0, 0, tzinfo=UTC)
    assert window_end == datetime(2026, 9, 21, 0, 0, tzinfo=UTC)


def _booking(*, service_name: str, start_time: datetime) -> Booking:
    """Build an in-memory Booking row, no DB required."""
    return Booking(
        customer_id=1,
        staff_id=1,
        service_name=service_name,
        start_time=start_time,
        status="confirmed",
    )


@pytest.mark.asyncio
async def test_get_dashboard_bookings_maps_repository_rows_in_order(monkeypatch) -> None:
    first = _booking(
        service_name="Haircut", start_time=datetime(2026, 9, 17, 9, 0, tzinfo=UTC)
    )
    second = _booking(
        service_name="Beard Trim", start_time=datetime(2026, 9, 17, 10, 30, tzinfo=UTC)
    )
    canned_rows = [
        (first, "Meena", "Priya"),
        (second, "Arjun", "Rahul"),
    ]

    async def _fake_list_bookings_with_names_in_window(db, *, window_start, window_end):
        return canned_rows

    monkeypatch.setattr(
        dashboard_domain,
        "list_bookings_with_names_in_window",
        _fake_list_bookings_with_names_in_window,
    )

    entries = await get_dashboard_bookings(db=None, view="today")

    assert entries == [
        DashboardBookingEntry(
            staff_name="Meena",
            customer_name="Priya",
            service_name="Haircut",
            start_time=first.start_time,
        ),
        DashboardBookingEntry(
            staff_name="Arjun",
            customer_name="Rahul",
            service_name="Beard Trim",
            start_time=second.start_time,
        ),
    ]


@pytest.mark.asyncio
async def test_get_dashboard_bookings_returns_empty_list_when_no_rows(monkeypatch) -> None:
    async def _fake_list_bookings_with_names_in_window(db, *, window_start, window_end):
        return []

    monkeypatch.setattr(
        dashboard_domain,
        "list_bookings_with_names_in_window",
        _fake_list_bookings_with_names_in_window,
    )

    entries = await get_dashboard_bookings(db=None, view="week")

    assert entries == []
