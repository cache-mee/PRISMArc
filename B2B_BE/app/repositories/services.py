from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Service


async def list_services(session: AsyncSession) -> list[Service]:
    result = await session.execute(select(Service).order_by(Service.name))
    return list(result.scalars().all())
