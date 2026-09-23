from datetime import datetime

from pydantic import BaseModel

from app.domain.appointments import ResolvedBookingCandidate


class AlternativeSlotSuggestion(BaseModel):
    """A proposed nearest-alternative slot awaiting the SM-4b checkpoint.

    Populated by the (not-yet-built) Story 2.7/FR-8 nearest-alternative
    reasoning once the Customer's originally-``requested_time`` turns out to
    be unavailable. Reuses the existing FR-6 ``ResolvedBookingCandidate``
    (``app.domain.appointments``) for the alternative slot itself rather than
    duplicating that shape.
    """

    requested_time: datetime
    unavailable_reason: str
    alternative: ResolvedBookingCandidate


class AlternativeSlotNotVerifiedError(ValueError):
    """Raised when an alternative-slot suggestion is acted on without human verification.

    Enforces SM-4b: no "offer to customer" step may run on an
    ``AlternativeSlotSuggestion`` until a human has reviewed or corrected it
    and ``VerifiedAlternativeSlotSuggestion.verified`` is ``True``.
    """


class VerifiedAlternativeSlotSuggestion(BaseModel):
    """An ``AlternativeSlotSuggestion`` awaiting the SM-4b human-verification checkpoint.

    Mirrors ``VerifiedBookingIntent``'s shape: the upstream step (a human
    operator, not the Customer — SM-4b is explicitly not customer-visible)
    is responsible for reviewing or correcting ``suggestion`` and setting
    ``verified`` to ``True`` before any "offer alternative to customer" step
    (part of Story 2.7/FR-8 itself) is allowed to act on it.
    """

    suggestion: AlternativeSlotSuggestion
    verified: bool = False


def require_verified_alternative_slot(
    verified_suggestion: VerifiedAlternativeSlotSuggestion,
) -> AlternativeSlotSuggestion:
    """Return the checked ``AlternativeSlotSuggestion`` once SM-4b's checkpoint has passed.

    Raises ``AlternativeSlotNotVerifiedError`` if
    ``verified_suggestion.verified`` is not ``True`` rather than letting any
    caller act on the suggestion — this is the single place SM-4b's
    guarantee ("a human reviews the FR-8 alternative-slot reasoning before
    it's offered to the customer") is enforced.
    """
    if verified_suggestion.verified is not True:
        raise AlternativeSlotNotVerifiedError(
            "Cannot act on an AlternativeSlotSuggestion that has not passed "
            "SM-4b human verification."
        )
    return verified_suggestion.suggestion
