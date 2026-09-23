from app.models.staff import StaffRole

_DECLINE_MESSAGE = (
    "I can only share your own schedule — I'm not able to show the full staff "
    "list or another staff member's information."
)


def decline_staff_dashboard_request(role: StaffRole) -> str | None:
    """Return a decline message for a Staff-mode dashboard/staff-list/other-schedule request (FR-29).

    Returns a fixed decline string when ``role`` is ``StaffRole.STAFF``; returns ``None`` for
    ``StaffRole.OWNER_ADMIN`` (Owner/Admin dashboard access is out of scope for this guard —
    see the FR-29 implementation plan's Out of Scope). Call sites are expected to consult this
    before ever returning staff-list, another-staff-member's-schedule, or dashboard-equivalent
    content to a Staff-identified session, and to return the decline string as-is instead of
    proceeding when it is not ``None``.
    """
    if role is StaffRole.STAFF:
        return _DECLINE_MESSAGE
    return None
