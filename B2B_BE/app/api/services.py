from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.tools.services import ServiceCatalogItem, get_service_catalog

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[ServiceCatalogItem])
async def browse_services(
    session: AsyncSession = Depends(get_session),
) -> list[ServiceCatalogItem]:
    """FR-4: current service catalog (name + price), reflecting latest DB state."""
    return await get_service_catalog(session)
