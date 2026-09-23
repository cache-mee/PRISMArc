from pydantic import BaseModel

from app.agent.booking_intent import BookingIntent


class BookingIntentNotVerifiedError(ValueError):
    """Raised when parsed booking intent is acted on without human verification.

    Enforces SM-4a: no availability-resolution step (FR-6/7/8) may run on a
    ``BookingIntent`` until a human has reviewed or corrected it and
    ``VerifiedBookingIntent.verified`` is ``True``.
    """


class VerifiedBookingIntent(BaseModel):
    """A parsed ``BookingIntent`` awaiting the SM-4a human-verification checkpoint.

    Mirrors ``ProposedAvailabilityChange``'s shape: the upstream step (a
    human operator, not the Customer — SM-4a is explicitly not
    customer-visible) is responsible for reviewing or correcting ``intent``
    and setting ``verified`` to ``True`` before any Story 2.5/2.6/2.7
    (FR-6/7/8) availability-resolution code is allowed to act on it.
    """

    intent: BookingIntent
    verified: bool = False


def require_verified_intent(verified_intent: VerifiedBookingIntent) -> BookingIntent:
    """Return the checked ``BookingIntent`` once SM-4a's checkpoint has passed.

    Raises ``BookingIntentNotVerifiedError`` if ``verified_intent.verified``
    is not ``True`` rather than letting any caller act on the parsed intent —
    this is the single place SM-4a's guarantee ("a human reviews/corrects the
    parsed intent before Stories 2.5/2.6/2.7 proceed") is enforced.
    """
    if verified_intent.verified is not True:
        raise BookingIntentNotVerifiedError(
            "Cannot act on a BookingIntent that has not passed SM-4a human verification."
        )
    return verified_intent.intent
