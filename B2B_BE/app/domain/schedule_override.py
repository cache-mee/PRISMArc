from app.models.staff import StaffRole

_DECLINE_MESSAGE = (
    "I can only make changes to your own schedule — I'm not able to update "
    "another staff member's availability."
)


def decline_staff_schedule_override(
    speaker_name: str, speaker_role: StaffRole, target_staff_name: str
) -> str | None:
    """Return a decline message when a Staff speaker names a schedule other than their own (FR-30).

    Returns a fixed decline string when ``speaker_role`` is ``StaffRole.STAFF`` and
    ``target_staff_name`` does not match ``speaker_name``; returns ``None`` when the names
    match, or when ``speaker_role`` is ``StaffRole.OWNER_ADMIN`` (Owner/Admin is not
    restricted by FR-30 — this is a Staff-to-Staff peer boundary, per the ticket text). Call
    sites are expected to consult this before ever applying a ``ProposedAvailabilityChange``,
    and to return the decline string as-is instead of proceeding when it is not ``None``.
    """
    if speaker_role is StaffRole.STAFF and speaker_name != target_staff_name:
        return _DECLINE_MESSAGE
    return None
