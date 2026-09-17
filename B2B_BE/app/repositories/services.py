from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Service


async def list_services(session: AsyncSession) -> list[Service]:
    result = await session.execute(select(Service).order_by(Service.name))
    return list(result.scalars().all())


async def create_service(db: AsyncSession, *, name: str, price: float) -> Service:
    """Insert a new Service row and return the persisted, refreshed instance.

    The sole insert path for a ``Service`` row (mirrors
    ``app.repositories.availability.create_availability``'s ``db.add`` /
    ``await db.commit()`` / ``await db.refresh()`` pattern).
    """
    service = Service(name=name, price=price)
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service
