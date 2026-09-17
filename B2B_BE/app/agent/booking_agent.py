from pydantic import BaseModel

from app.domain.appointments import ResolvedBookingCandidate, render_direct_confirmation


class DirectConfirmationPrompt(BaseModel):
    """The FR-6 direct-confirmation prompt awaiting the Customer's answer."""

    candidate: ResolvedBookingCandidate
    message: str
    confirmed: bool = False


def confirm_exact_match(
    candidate: ResolvedBookingCandidate,
) -> DirectConfirmationPrompt:
    """Render the FR-6 confirmation for a resolved candidate.

    This is the hook point a future conversational Booking Agent loop will
    call once intent parsing, staff-preference limiting, the SM-4a
    checkpoint, and an actual availability check have all resolved to one
    candidate slot. `confirmed` stays False until the Customer explicitly
    confirms; no Booking write may proceed before that.
    """
    message = render_direct_confirmation(candidate)
    return DirectConfirmationPrompt(candidate=candidate, message=message)
