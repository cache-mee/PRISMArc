from datetime import datetime

from pydantic import BaseModel

from app.domain.alternative_slot_verification import VerifiedAlternativeSlotSuggestion


class VerifyAlternativeSlotArgs(BaseModel):
    """LLM-callable tool arguments for the SM-4b human-verification checkpoint.

    Any of ``unavailable_reason``/``alternative_start_time``/
    ``alternative_staff_name`` left ``None`` keeps the originally-suggested
    value; a human operator sets one to correct it. ``verified`` is the
    explicit human decision to let the alternative-slot suggestion proceed.
    """

    unavailable_reason: str | None = None
    alternative_start_time: datetime | None = None
    alternative_staff_name: str | None = None
    verified: bool


def verify_alternative_slot(
    pending: VerifiedAlternativeSlotSuggestion, args: VerifyAlternativeSlotArgs
) -> VerifiedAlternativeSlotSuggestion:
    """Apply a human operator's SM-4b review/correction to a pending AlternativeSlotSuggestion.

    This is the in-process tool seam a future Manager Agent (operator-facing,
    never the customer-facing Booking Agent — SM-4b is explicitly not
    customer-visible) registers to let a human review or correct the
    suggested alternative slot and set ``verified``. No DB access is needed:
    correcting or verifying a suggestion is pure data transformation,
    enforced downstream by
    ``app.domain.alternative_slot_verification.require_verified_alternative_slot``.
    """
    alternative_corrections = {
        field: value
        for field, value in (
            ("start_time", args.alternative_start_time),
            ("staff_name", args.alternative_staff_name),
        )
        if value is not None
    }
    corrected_alternative = pending.suggestion.alternative.model_copy(
        update=alternative_corrections
    )

    suggestion_corrections = {"alternative": corrected_alternative}
    if args.unavailable_reason is not None:
        suggestion_corrections["unavailable_reason"] = args.unavailable_reason

    corrected_suggestion = pending.suggestion.model_copy(update=suggestion_corrections)
    return VerifiedAlternativeSlotSuggestion(
        suggestion=corrected_suggestion, verified=args.verified
    )
