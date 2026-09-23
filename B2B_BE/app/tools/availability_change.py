"""LLM-callable availability-change tools (FR-25/FR-27, APPOINTMEN-55).

The ticket's own worked example — Dr. Rao (Staff) says "I'm unavailable Friday
morning"; the Manager Agent turns that into a ``ProposedAvailabilityChange``,
restates it, gets explicit confirmation, and only then calls
``app.domain.availability.confirm_and_apply_availability_change`` (the FR-27
gate) — has no registrable tool until this module. ``propose_availability_change``
and ``confirm_availability_change`` are the two halves of that path: the first
turns free text into a pending change held on ``SessionState`` (Task 1); the
second reads that pending change back, records the human's explicit yes/no,
and only on a "yes" performs the real write.

Both tools re-consult the existing FR-21/FR-30 guard functions
(``decline_owner_admin_own_availability_request``,
``decline_staff_schedule_override``) immediately before acting, as
defense-in-depth alongside the future role-scoped tool registry's (Task 4)
role-based visibility — belt-and-braces, not a replacement for either: a role
that should never be offered these tools in the first place is still refused
here if it somehow reaches them.
"""

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.manager_agent import (
    SpeakerContext,
    render_proposed_availability_change_restatement,
)
from app.agent.state import session_store
from app.domain.availability import (
    ProposedAvailabilityChange,
    confirm_and_apply_availability_change,
)
from app.domain.owner_admin_availability_boundary import (
    decline_owner_admin_own_availability_request,
)
from app.domain.schedule_override import decline_staff_schedule_override


class NoPendingAvailabilityChangeError(RuntimeError):
    """Raised when ``confirm_availability_change`` is called with nothing pending.

    ``confirm_and_apply_availability_change`` (``app.domain.availability``)
    requires an actual ``ProposedAvailabilityChange``; this module refuses to
    call it with ``None`` rather than letting an ``AttributeError`` surface
    from deep inside the domain layer.
    """


def _first_guard_decline(speaker: SpeakerContext, target_staff_name: str) -> str | None:
    """Re-consult the FR-21/FR-30 guards for ``speaker`` acting on ``target_staff_name``.

    Checks FR-21 (Owner/Admin cannot manage their own availability) first,
    then FR-30 (a Staff member cannot alter another staff member's
    schedule) — returns the first non-``None`` decline string, or ``None``
    when both guards clear the action.
    """
    decline = decline_owner_admin_own_availability_request(speaker.role)
    if decline is not None:
        return decline
    return decline_staff_schedule_override(
        speaker.name, speaker.role, target_staff_name
    )


class ProposeAvailabilityChangeArgs(BaseModel):
    """LLM-callable tool arguments for proposing an availability change (FR-25).

    Filled directly by the Manager Agent loop model from the speaker's free-text
    block/unblock request (e.g. "I'm unavailable Friday morning") — the live current
    date/time it needs to resolve a relative phrase against is given to it in its own
    system prompt. Deliberately has no staff-identity field of any kind: whose schedule
    is being changed is never taken from the model's args, only ever from the
    already-resolved ``speaker`` passed alongside these args — this is what keeps FR-30's
    "a staff member cannot alter another staff member's schedule" boundary intact even
    against args that named someone else.
    """

    start_time: datetime
    end_time: datetime
    blocked: bool


async def propose_availability_change(
    session_id: str,
    speaker: SpeakerContext,
    args: ProposeAvailabilityChangeArgs,
) -> dict:
    """Turn ``args`` into a pending ``ProposedAvailabilityChange`` (FR-25).

    Re-consults the FR-21/FR-30 guards for ``speaker`` before ever building a
    change; a decline short-circuits with no session mutation and no restated
    text to relay. Otherwise builds the change directly from ``args`` and
    ``speaker.name`` (never from a model-supplied identity field — see
    ``ProposeAvailabilityChangeArgs``), stores it on the session as
    ``SessionState.pending_availability_change`` (unconfirmed), and returns
    the restatement text for the model to relay back to ``speaker`` — the
    "restate" half of FR-27's restate-then-confirm sequence.
    """
    guard_decline = _first_guard_decline(speaker, speaker.name)
    if guard_decline is not None:
        return {"declined": True, "message": guard_decline}

    change = ProposedAvailabilityChange(
        staff_name=speaker.name,
        start_time=args.start_time,
        end_time=args.end_time,
        blocked=args.blocked,
        confirmed=False,
    )

    state = session_store.get_or_create(session_id)
    state.pending_availability_change = change
    session_store.save(session_id, state)

    restatement = render_proposed_availability_change_restatement(change)
    return {"declined": False, "restatement": restatement}


class ConfirmAvailabilityChangeArgs(BaseModel):
    """LLM-callable tool arguments for confirming/declining a pending change (FR-27).

    Mirrors ``ConfirmCatalogChangeArgs``'s "nothing to correct, only to
    confirm" shape: a restated availability change is the speaker's own
    proposal read back to them, not deterministic data a human corrects, so
    there is nothing here beyond their explicit yes/no.
    """

    confirmed: bool


async def confirm_availability_change(
    db: AsyncSession,
    session_id: str,
    speaker: SpeakerContext,
    args: ConfirmAvailabilityChangeArgs,
) -> dict:
    """Record ``speaker``'s explicit yes/no on the session's pending change (FR-27).

    Raises ``NoPendingAvailabilityChangeError`` when
    ``SessionState.pending_availability_change`` is ``None`` — there is
    nothing to confirm or decline, and this refuses to call
    ``confirm_and_apply_availability_change`` with ``None`` rather than
    letting an unhandled error surface from the domain layer.

    Re-consults the FR-21/FR-30 guards for ``speaker`` acting on the pending
    change's ``staff_name`` before acting either way. The pending change is
    always cleared from the session afterward — a decline
    (``args.confirmed=False``) is recorded as an explicit "no" and the
    change discarded, never a silent drop; a confirmation
    (``args.confirmed=True``) additionally calls
    ``confirm_and_apply_availability_change`` to perform the real write, the
    single point FR-27's guarantee is enforced.
    """
    state = session_store.get_or_create(session_id)
    pending = state.pending_availability_change
    if pending is None:
        raise NoPendingAvailabilityChangeError(
            f"No pending availability change to confirm for session_id={session_id!r}."
        )

    guard_decline = _first_guard_decline(speaker, pending.staff_name)
    if guard_decline is not None:
        return {"declined": True, "message": guard_decline}

    if not args.confirmed:
        state.pending_availability_change = None
        session_store.save(session_id, state)
        return {"confirmed": False, "applied": False}

    confirmed_change = ProposedAvailabilityChange(
        staff_name=pending.staff_name,
        start_time=pending.start_time,
        end_time=pending.end_time,
        blocked=pending.blocked,
        confirmed=True,
    )
    availability = await confirm_and_apply_availability_change(db, confirmed_change)

    state.pending_availability_change = None
    session_store.save(session_id, state)
    return {
        "confirmed": True,
        "applied": True,
        "availability_id": availability.id,
    }
