from pydantic import BaseModel

from app.domain.conflict_verification import VerifiedConflictCheck


class VerifyConflictCheckArgs(BaseModel):
    """LLM-callable tool arguments for the SM-4c human-verification checkpoint.

    Unlike SM-4a's parsed-intent verification (where a human corrects a
    misparsed value), a ``ConflictCheckResult`` is deterministic data read
    directly from existing ``Booking`` rows — there is nothing for a human
    operator/judge to correct here, only to review and explicitly sign off
    on. Hence the single ``verified`` field.
    """

    verified: bool


def verify_conflict_check(
    pending: VerifiedConflictCheck, args: VerifyConflictCheckArgs
) -> VerifiedConflictCheck:
    """Record a human operator/judge's SM-4c decision on a pending conflict check.

    This is the in-process tool seam a future Manager Agent loop registers for the
    operator/judge role to act on ``present_conflict_check_for_verification``'s output
    (``app.agent.manager_agent``). Returns a new ``VerifiedConflictCheck`` carrying the
    same ``pending.result`` and ``verified=args.verified`` — a pure data transformation,
    no DB access, since the underlying ``ConflictCheckResult`` was already read from
    ``Booking`` rows upstream by ``check_conflicts`` (``app.domain.conflicts``).

    An operator can explicitly decline to clear a conflict (``args.verified=False``):
    that decision is recorded via the returned wrapper, not silently dropped, matching
    FR-26's "not a silent rejection" spirit.
    """
    return VerifiedConflictCheck(result=pending.result, verified=args.verified)
