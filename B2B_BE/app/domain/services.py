from pydantic import BaseModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Service
from app.repositories.services import (
    create_service,
    deactivate_service,
    get_service_by_id,
    update_service,
)


class ServiceNotConfirmedError(ValueError):
    """Raised when a Service write is attempted without an explicit confirmation.

    Enforces FR-15: no Service record may be created until
    ``ProposedService.confirmed`` is ``True``.
    """


class ServiceNotFoundError(ValueError):
    """Raised when a referenced Service id does not match any existing row.

    Mirrors ``BookingNotFoundError`` in ``app.domain.appointments``.
    """


class ServiceEditNotConfirmedError(ValueError):
    """Raised when a Service edit is attempted without an explicit confirmation.

    Enforces FR-16: no Service row's ``name``/``price`` may change until
    ``ProposedServiceEdit.confirmed`` is ``True``. Kept distinct from
    ``ServiceNotConfirmedError``, which stays scoped to the create path
    (FR-15).
    """


class ServiceDeletionNotConfirmedError(ValueError):
    """Raised when a Service deletion is attempted without an explicit confirmation.

    Enforces FR-17: no Service row's ``is_active`` may flip to ``False``
    until ``ProposedServiceDeletion.confirmed`` is ``True``. Kept distinct
    from ``ServiceNotConfirmedError`` (create, FR-15) and
    ``ServiceEditNotConfirmedError`` (edit, FR-16).
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


class ProposedServiceEdit(BaseModel):
    """An already-restated Service edit awaiting explicit confirmation.

    Mirrors ``ProposedService``'s shape, adapted for update: the upstream
    conversational step (APPOINTMEN-40, not built here) is responsible for
    restating the new name/price to Ramesh and setting ``confirmed`` to
    ``True`` once he agrees.
    """

    service_id: int
    new_name: str | None = None
    new_price: float | None = None
    confirmed: bool = False

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> "ProposedServiceEdit":
        """Reject construction unless at least one of new_name/new_price is set.

        This is a structural precondition on the shape of the proposed edit
        itself (an edit naming neither field is not a valid proposal at
        all), not a business rule about *when* a write is allowed — so it is
        enforced here, at construction time, rather than inside
        ``confirm_and_update_service``.
        """
        if self.new_name is None and self.new_price is None:
            raise ValueError(
                "ProposedServiceEdit requires at least one of new_name or "
                "new_price to be set."
            )
        return self


async def confirm_and_update_service(
    db: AsyncSession, proposed: ProposedServiceEdit
) -> Service:
    """Update a Service row from a confirmed proposed edit (FR-16).

    Raises ``ServiceEditNotConfirmedError`` if ``proposed.confirmed`` is not
    ``True`` rather than touching the database at all. Otherwise looks up
    the row via ``get_service_by_id``, raising ``ServiceNotFoundError`` if
    ``proposed.service_id`` matches no row. Otherwise applies the update via
    ``update_service``, passing ``proposed.new_name``/``proposed.new_price``
    straight through unchanged.

    This is the single place FR-16's guarantee ("prior price/name no longer
    returned by Story 2.1 once confirmed and applied") is enforced.
    """
    if proposed.confirmed is not True:
        raise ServiceEditNotConfirmedError(
            "Cannot update a Service from an unconfirmed ProposedServiceEdit."
        )

    service = await get_service_by_id(db, proposed.service_id)
    if service is None:
        raise ServiceNotFoundError(
            f"No Service record found for service_id={proposed.service_id!r}."
        )

    return await update_service(
        db, service, name=proposed.new_name, price=proposed.new_price
    )


class ProposedServiceDeletion(BaseModel):
    """An already-restated Service removal awaiting explicit confirmation.

    Mirrors ``ProposedService``/``ProposedServiceEdit``'s shape, adapted for
    deletion: the upstream conversational step (APPOINTMEN-40, not built
    here) is responsible for restating the removal to Ramesh and setting
    ``confirmed`` to ``True`` once he agrees. No ``model_validator`` is
    needed — unlike ``ProposedServiceEdit``, there is no "at least one
    field" shape constraint; ``service_id`` alone is the entire payload.
    """

    service_id: int
    confirmed: bool = False


async def confirm_and_delete_service(
    db: AsyncSession, proposed: ProposedServiceDeletion
) -> Service:
    """Deactivate a Service row from a confirmed proposed deletion (FR-17).

    Raises ``ServiceDeletionNotConfirmedError`` if ``proposed.confirmed`` is
    not ``True`` rather than touching the database at all. Otherwise looks
    up the row via ``get_service_by_id``, raising ``ServiceNotFoundError``
    if ``proposed.service_id`` matches no row. Otherwise calls
    ``deactivate_service`` and returns the deactivated row.

    This is the single place FR-17's guarantee ("removed service no longer
    offered or returned by Story 2.1 after confirmation") is enforced. The
    row is soft-deleted (``is_active`` flipped to ``False``), never
    hard-deleted, since a hard delete would violate
    ``bookings.service_id``'s FK for any service still referenced by an
    existing booking.
    """
    if proposed.confirmed is not True:
        raise ServiceDeletionNotConfirmedError(
            "Cannot delete a Service from an unconfirmed ProposedServiceDeletion."
        )

    service = await get_service_by_id(db, proposed.service_id)
    if service is None:
        raise ServiceNotFoundError(
            f"No Service record found for service_id={proposed.service_id!r}."
        )

    return await deactivate_service(db, service)
