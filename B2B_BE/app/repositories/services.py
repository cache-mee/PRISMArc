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


async def get_service_by_id(db: AsyncSession, service_id: int) -> Service | None:
    """Return the Service row matching service_id, or None if not found.

    Mirrors ``app.repositories.bookings.get_booking_by_id``'s shape exactly.
    """
    stmt = select(Service).where(Service.id == service_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def update_service(
    db: AsyncSession,
    service: Service,
    *,
    name: str | None = None,
    price: float | None = None,
) -> Service:
    """Set whichever of an already-fetched Service's name/price were supplied.

    Mirrors ``app.repositories.bookings.set_booking_status``'s "already-
    fetched instance in, mutate, commit, refresh, return" shape. Sets
    ``service.name``/``service.price`` only for whichever keyword argument
    is not ``None`` — at least one is guaranteed non-``None`` by the domain
    layer before this is called, so this function performs no "nothing to
    update" guard of its own.
    """
    if name is not None:
        service.name = name
    if price is not None:
        service.price = price
    await db.commit()
    await db.refresh(service)
    return service
