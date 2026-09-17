from pydantic import BaseModel

from app.domain.conflicts import ConflictCheckResult


class ConflictCheckNotVerifiedError(ValueError):
    """Raised when a conflict-check outcome is acted on without human verification.

    Enforces SM-4c: no downstream write (FR-27/FR-9) may treat a
    ``ConflictCheckResult`` as cleared until a human has reviewed it and
    ``VerifiedConflictCheck.verified`` is ``True``.
    """


class VerifiedConflictCheck(BaseModel):
    """A ``ConflictCheckResult`` awaiting the SM-4c human-verification checkpoint.

    Mirrors ``VerifiedBookingIntent``'s shape (SM-4a): the upstream step (a
    human operator/judge, not staff or a customer — SM-4c is explicitly not
    staff-visible) is responsible for reviewing ``result`` and setting
    ``verified`` to ``True`` before any FR-27/FR-9 write code is allowed to
    act on it.
    """

    result: ConflictCheckResult
    verified: bool = False


def require_verified_conflict_check(
    verified_check: VerifiedConflictCheck,
) -> ConflictCheckResult:
    """Return the checked ``ConflictCheckResult`` once SM-4c's checkpoint has passed.

    Raises ``ConflictCheckNotVerifiedError`` if ``verified_check.verified``
    is not ``True`` rather than letting any caller act on the conflict-check
    outcome — this is the single place SM-4c's guarantee ("a human reviews
    the FR-26 conflict-detection outcome before FR-27/FR-9 is finalized") is
    enforced.
    """
    if verified_check.verified is not True:
        raise ConflictCheckNotVerifiedError(
            "Cannot act on a ConflictCheckResult that has not passed SM-4c human verification."
        )
    return verified_check.result
