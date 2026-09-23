from datetime import datetime

from pydantic import BaseModel

from app.domain.booking_intent_verification import VerifiedBookingIntent


class VerifyBookingIntentArgs(BaseModel):
    """LLM-callable tool arguments for the SM-4a human-verification checkpoint.

    Any of ``service_name``/``requested_time``/``staff_preference`` left
    ``None`` keeps the originally-parsed value; a human operator sets one to
    correct it. ``verified`` is the explicit human decision to let the
    intent proceed.
    """

    service_name: str | None = None
    requested_time: datetime | None = None
    staff_preference: str | None = None
    verified: bool


def verify_booking_intent(
    pending: VerifiedBookingIntent, args: VerifyBookingIntentArgs
) -> VerifiedBookingIntent:
    """Apply a human operator's SM-4a review/correction to a pending BookingIntent.

    This is the in-process tool seam a future Manager Agent (operator-facing,
    never the customer-facing Booking Agent — SM-4a is explicitly not
    customer-visible) registers to let a human review or correct the parsed
    intent and set ``verified``. No DB access is needed: correcting or
    verifying parsed intent is pure data transformation, enforced downstream
    by ``app.domain.booking_intent_verification.require_verified_intent``.
    """
    corrections = {
        field: value
        for field, value in (
            ("service_name", args.service_name),
            ("requested_time", args.requested_time),
            ("staff_preference", args.staff_preference),
        )
        if value is not None
    }
    corrected_intent = pending.intent.model_copy(update=corrections)
    return VerifiedBookingIntent(intent=corrected_intent, verified=args.verified)
