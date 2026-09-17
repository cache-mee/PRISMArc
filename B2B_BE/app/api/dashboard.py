from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.dashboard import (
    DashboardBookingEntry,
    DashboardStaffStatus,
    DashboardView,
    get_dashboard_bookings,
    get_dashboard_staff_status,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/staff", response_model=list[DashboardStaffStatus])
async def get_staff_status(
    session: AsyncSession = Depends(get_db),
) -> list[DashboardStaffStatus]:
    """FR-19: current status (blocked/available, today's booking count) of
    every Dashboard-visible staff member."""
    return await get_dashboard_staff_status(session)


@router.get("/bookings", response_model=list[DashboardBookingEntry])
async def get_bookings(
    view: DashboardView = "today",
    session: AsyncSession = Depends(get_db),
) -> list[DashboardBookingEntry]:
    """FR-20: flat, chronological list of confirmed bookings for
    ``view=today`` (default) or ``view=week``."""
    return await get_dashboard_bookings(session, view)
