from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.services import list_services


class ServiceCatalogItem(BaseModel):
    name: str
    price: float


async def get_service_catalog(session: AsyncSession) -> list[ServiceCatalogItem]:
    """Tool for the Booking Agent: current service catalog (FR-4).

    Reads through app.repositories.services — never queries the DB directly —
    so the LLM tool-calling layer stays out of the data-access path.
    """
    services = await list_services(session)
    return [ServiceCatalogItem(name=s.name, price=float(s.price)) for s in services]
