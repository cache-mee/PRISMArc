from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Service
from app.repositories.services import create_service


class ServiceNotConfirmedError(ValueError):
    """Raised when a Service write is attempted without an explicit confirmation.

    Enforces FR-15: no Service record may be created until
    ``ProposedService.confirmed`` is ``True``.
    """


class ProposedService(BaseModel):
    """An already-restated new service awaiting explicit confirmation.

    Mirrors ``ProposedAvailabilityChange``'s shape: the upstream
    conversational step (APPOINTMEN-40, not built here) is responsible for
    restating the name/price to Ramesh and setting ``confirmed`` to ``True``
    once he agrees.
    """

    name: str
    price: float
    confirmed: bool = False


async def confirm_and_create_service(
    db: AsyncSession, proposed: ProposedService
) -> Service:
    """Create a Service row from a confirmed proposed service (FR-15).

    Raises ``ServiceNotConfirmedError`` if ``proposed.confirmed`` is not
    ``True`` rather than touching the database at all — this is the single
    place FR-15's guarantee ("the new service does not exist in the Shared
    Data Store until Ramesh explicitly confirms the agent's restated
    details") is enforced.

    Unlike Booking/Availability, ``Service`` has no owning foreign key, so no
    staff/customer resolution step is needed here.
    """
    if proposed.confirmed is not True:
        raise ServiceNotConfirmedError(
            "Cannot create a Service from an unconfirmed ProposedService."
        )

    return await create_service(db, name=proposed.name, price=proposed.price)
