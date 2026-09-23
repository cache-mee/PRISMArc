from app.models.staff import StaffRole

_DECLINE_MESSAGE = (
    "Availability block/unblock isn't something you manage directly — that's "
    "handled per-Staff-member."
)


def decline_owner_admin_own_availability_request(speaker_role: StaffRole) -> str | None:
    """Return a decline message for an Owner/Admin block/unblock-availability request (FR-21).

    Returns a fixed decline string when ``speaker_role`` is ``StaffRole.OWNER_ADMIN``; returns
    ``None`` for ``StaffRole.STAFF`` (managing one's own availability is exactly what a Staff
    speaker is permitted to do — see the FR-21 implementation plan's Out of Scope). Call sites
    are expected to consult this before ever building or applying a ``ProposedAvailabilityChange``
    for the speaker, and to return the decline string as-is instead of proceeding when it is not
    ``None``.
    """
    if speaker_role is StaffRole.OWNER_ADMIN:
        return _DECLINE_MESSAGE
    return None
