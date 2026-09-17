"""``GET /dashboard/staff`` — read-only Dashboard staff-list endpoint (APPOINTMEN-56, FR-19).

Per `base-rules.md`'s router conventions (mirrors `app.api.services`): a thin
`APIRouter` handler that reuses the existing, already read-only
``list_dashboard_staff`` (``app.repositories.staff_repository``) — which
already excludes the Owner/Admin (PRD §9.1 Decision 1) — and maps the result
to a small Pydantic response model. No new repository or mutation logic is
introduced here.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.staff import StaffRole
from app.repositories.staff_repository import list_dashboard_staff

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class StaffListItem(BaseModel):
    id: int
    name: str
    role: StaffRole


@router.get("/staff", response_model=list[StaffListItem])
async def get_dashboard_staff(
    session: AsyncSession = Depends(get_db),
) -> list[StaffListItem]:
    """FR-19: current staff roster for the Owner Dashboard (excludes Owner/Admin)."""
    staff = await list_dashboard_staff(session)
    return [StaffListItem(id=member.id, name=member.name, role=member.role) for member in staff]
