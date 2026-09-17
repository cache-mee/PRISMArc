"""Booking Agent turn logic — FR-1's identity-resolution gate (APPOINTMEN-14).

``handle_message`` is the one deterministic state machine implementing all
three of FR-1's acceptance criteria, per the UX spec
(`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/customer-booking-chat.md`
§3.1):

1. Before any booking/browse-history/cancel/reschedule action, the agent
   always asks for a phone number first (AC1).
2. A phone number matching an existing ``Customer`` record greets the
   Customer by name and proceeds straight to the stated intent — no name
   question is ever asked (AC2).
3. A phone number with no match hands off to Story 1.3 (FR-2) — this ticket
   only defines and calls that hand-off point, it does not implement it
   (AC3).

No real booking/browse/cancel/reschedule logic is implemented here (Epic
2/3, out of scope) — once a session is resolved, this module returns a
placeholder acknowledgement only. The important, in-scope guarantee is that
the identity gate above runs first, every time, before that placeholder (or
any future real intent handling) executes.
"""

from sqlalchemy.orm import Session

from app.agent.state import session_store
from app.domain.identity import resolve_customer_by_phone

_ASK_PHONE_NUMBER = "Could I get your phone number to pull up your account?"
_NEW_CUSTOMER_INTERIM = "I don't have that number on file yet — what's your name?"
_ALREADY_RESOLVED_PLACEHOLDER = "Got it — what would you like to do?"


def hand_off_to_new_customer_flow(session_id: str, phone_number: str) -> None:
    """Hand off an unresolved phone number to the new-customer flow.

    Implemented by Story 1.3 (FR-2) — this ticket only defines the call
    site. Story 1.3 owns the actual name-capture turn and ``Customer``
    record creation; this stub deliberately does neither.
    """
    return None


def handle_message(db: Session, session_id: str, message: str | None) -> str:
    """Run one Booking Agent turn for ``session_id``.

    - No ``message`` (the opening turn) always returns the phone-number
      prompt, without touching identity resolution (AC1).
    - Once the session is ``resolved``, the identity gate no longer applies
      and no further phone-number question is ever asked (AC2).
    - Otherwise, ``message`` is treated as the phone number and resolved
      against ``app.domain.identity.resolve_customer_by_phone``: a match
      greets the Customer by name and marks the session resolved (AC2); no
      match calls the ``hand_off_to_new_customer_flow`` stub and returns the
      interim new-customer reply, without marking the session resolved
      (AC3).
    """
    state = session_store.get_or_create(session_id)

    if message is None:
        return _ASK_PHONE_NUMBER

    if state.resolved:
        return _ALREADY_RESOLVED_PLACEHOLDER

    phone_number = message
    customer = resolve_customer_by_phone(db, phone_number)

    if customer is not None:
        state.phone_number = phone_number
        state.customer_id = customer.id
        state.customer_name = customer.name
        state.resolved = True
        session_store.save(session_id, state)
        return (
            f"Welcome back, {customer.name}! What can I help with — booking, "
            "browsing services, or checking your appointments?"
        )

    state.phone_number = phone_number
    session_store.save(session_id, state)
    hand_off_to_new_customer_flow(session_id, phone_number)
    return _NEW_CUSTOMER_INTERIM
