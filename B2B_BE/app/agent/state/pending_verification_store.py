"""Interim, in-process store for the current SM-4a/b/c pending-verification item.

``verify_booking_intent`` / ``verify_alternative_slot`` / ``verify_conflict_check``
(``app.tools.intent_verification`` / ``alternative_slot_verification`` /
``conflict_verification``) each take a ``pending: VerifiedXxx``-shaped object as
their first argument — not something an LLM tool call can supply directly,
since it isn't part of a JSON tool schema. This module holds "the current
pending item awaiting verification" for the Manager Agent loop's dispatch step
(``app.agent.tool_registry``) to read.

APPOINTMEN-54 (Booking Agent conversational loop, not yet implemented — or
whatever ticket ends up producing these items for real) is the eventual real
producer of these items and is expected to call the setters below. This
module does not itself decide when a new pending item appears; it only holds
whatever was last set.

Recorded explicitly as the same kind of in-process, single-current-item,
not-shared-across-worker-processes seam already accepted for
``app.agent.state.session_store`` (`stack/stack-proposal.md` §6.4) — one slot
per verification type, overwritten (not queued) on each ``set_*`` call.
"""

from app.domain.alternative_slot_verification import VerifiedAlternativeSlotSuggestion
from app.domain.booking_intent_verification import VerifiedBookingIntent
from app.domain.conflict_verification import VerifiedConflictCheck

_pending_booking_intent: VerifiedBookingIntent | None = None
_pending_alternative_slot: VerifiedAlternativeSlotSuggestion | None = None
_pending_conflict_check: VerifiedConflictCheck | None = None


def get_pending_booking_intent() -> VerifiedBookingIntent | None:
    """Return the current pending SM-4a item, or ``None`` if nothing is set."""
    return _pending_booking_intent


def set_pending_booking_intent(pending: VerifiedBookingIntent | None) -> None:
    """Set (or clear, with ``None``) the current pending SM-4a item.

    Overwrites any previously-set item — this store holds a single current
    item per verification type, not a queue.
    """
    global _pending_booking_intent
    _pending_booking_intent = pending


def get_pending_alternative_slot() -> VerifiedAlternativeSlotSuggestion | None:
    """Return the current pending SM-4b item, or ``None`` if nothing is set."""
    return _pending_alternative_slot


def set_pending_alternative_slot(
    pending: VerifiedAlternativeSlotSuggestion | None,
) -> None:
    """Set (or clear, with ``None``) the current pending SM-4b item.

    Overwrites any previously-set item — this store holds a single current
    item per verification type, not a queue.
    """
    global _pending_alternative_slot
    _pending_alternative_slot = pending


def get_pending_conflict_check() -> VerifiedConflictCheck | None:
    """Return the current pending SM-4c item, or ``None`` if nothing is set."""
    return _pending_conflict_check


def set_pending_conflict_check(pending: VerifiedConflictCheck | None) -> None:
    """Set (or clear, with ``None``) the current pending SM-4c item.

    Overwrites any previously-set item — this store holds a single current
    item per verification type, not a queue.
    """
    global _pending_conflict_check
    _pending_conflict_check = pending
