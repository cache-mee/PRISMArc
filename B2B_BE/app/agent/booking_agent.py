"""Booking Agent turn logic.

Houses four independent pieces of Booking Agent behavior added by separate
tickets:

- ``handle_message`` — FR-1's identity-resolution gate (APPOINTMEN-14),
  extended by APPOINTMEN-48 to be channel-aware (FR-3) without forking any
  logic per channel. The one deterministic state machine implementing all of
  FR-1/FR-3's acceptance criteria, per the UX spec
  (`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/customer-booking-chat.md`
  §3.1):

  1. Before any booking/browse-history/cancel/reschedule action, the agent
     always asks for a phone number first — unless the calling channel
     adapter already knows it (see ``phone_number`` below), in which case
     that question is skipped entirely (AC1/FR-3).
  2. A phone number matching an existing ``Customer`` record greets the
     Customer by name and proceeds straight to the stated intent — no name
     question is ever asked (AC2).
  3. A phone number with no match asks exactly one follow-up question (the
     Customer's name); the next turn's ``message`` is taken as that name,
     ``app.domain.customers.find_or_create_customer`` creates the
     ``Customer`` record, and the session is marked resolved with the same
     name-based greeting the known-number path uses (AC3).

  ``phone_number`` is an optional, keyword-only parameter representing a
  phone number the calling channel adapter already knows out-of-band (e.g.
  WhatsApp's webhook sender). When supplied, identity resolution runs
  against it immediately instead of asking for a number via ``message``.
  When absent (Web Chat's call site, unchanged), ``message`` itself is
  treated as the phone number once asked for, exactly as before.

  No real booking/browse/cancel/reschedule logic is implemented here (Epic
  2/3, out of scope) — once a session is resolved, this module returns a
  placeholder acknowledgement only. The important, in-scope guarantee is
  that the identity gate above runs first, every time, before that
  placeholder (or any future real intent handling) executes.

- ``present_intent_for_verification`` — the SM-4a human-verification
  checkpoint (APPOINTMEN-21) referenced by ``confirm_exact_match`` below.
  Logs a freshly-parsed ``BookingIntent`` (``app.agent.booking_intent``) as
  the observable checkpoint moment and returns it wrapped, unverified, in a
  ``VerifiedBookingIntent``. Not customer-visible. A human operator reviews
  or corrects it before ``app.domain.booking_intent_verification.require_verified_intent``
  will let any downstream code act on it.

- ``confirm_exact_match`` — FR-6's direct-confirmation prompt
  (APPOINTMEN-22). The hook point a future conversational Booking Agent
  loop will call once intent parsing, staff-preference limiting, the SM-4a
  checkpoint, and an actual availability check have all resolved to one
  candidate slot.

- ``present_nearest_alternatives`` — FR-8's nearest-alternative(s) message
  (APPOINTMEN-24). The hook point a future conversational Booking Agent
  loop will call instead of ``confirm_exact_match`` once intent parsing and
  the SM-4a checkpoint have determined the Customer's named exact time did
  not resolve directly — it names the reason the requested time is
  unavailable (already booked or blocked) and at least one concrete,
  bookable alternative, so a rejected exact-time request never dead-ends
  the conversation.

- ``list_day_slots`` — FR-7's day-only slot listing (APPOINTMEN-23). The
  hook point a future conversational Booking Agent loop will call once
  intent parsing has resolved a day-only (no exact time) request, mirroring
  ``confirm_exact_match``'s not-yet-wired-in posture.

- ``present_alternative_for_verification`` — the SM-4b human-verification
  checkpoint (APPOINTMEN-25) sitting between ``present_nearest_alternatives``'s
  Story 2.7/FR-8 nearest-alternative reasoning and the point that reasoning
  would be offered to the Customer. Logs a freshly-produced
  ``AlternativeSlotSuggestion`` (``app.domain.alternative_slot_verification``)
  as the observable checkpoint moment and returns it wrapped, unverified, in
  a ``VerifiedAlternativeSlotSuggestion``. Not customer-visible. A human
  operator reviews or corrects it before
  ``app.domain.alternative_slot_verification.require_verified_alternative_slot``
  will let any downstream "offer to customer" code act on it.

These pieces do not yet call each other — wiring the identity-resolved turn
loop into intent parsing, the SM-4a checkpoint, and booking
confirmation/alternatives/day-slot listing/the SM-4b checkpoint is future,
out-of-scope work (Epic 2/3).
"""

import logging
from datetime import date, datetime

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.booking_intent import BookingIntent
from app.agent.state import session_store
from app.domain.alternative_slot_verification import (
    AlternativeSlotSuggestion,
    VerifiedAlternativeSlotSuggestion,
)
from app.domain.appointments import (
    ResolvedBookingCandidate,
    find_nearest_alternatives,
    render_alternative_slots,
    render_direct_confirmation,
)
from app.domain.availability import (
    OpenSlot,
    list_open_slots_for_day,
    render_day_slot_list,
)
from app.domain.booking_intent_verification import VerifiedBookingIntent
from app.domain.customers import find_or_create_customer
from app.domain.identity import resolve_customer_by_phone

_logger = logging.getLogger(__name__)

_ASK_PHONE_NUMBER = "Could I get your phone number to pull up your account?"
_NEW_CUSTOMER_INTERIM = "I don't have that number on file yet — what's your name?"
_ALREADY_RESOLVED_PLACEHOLDER = "Got it — what would you like to do?"


def hand_off_to_new_customer_flow(session_id: str, phone_number: str) -> None:
    """Mark that ``session_id`` has handed off to the new-customer flow.

    Originally a Story 1.3 (FR-2) stub; APPOINTMEN-48 implements the actual
    name-capture turn and ``Customer`` record creation directly in
    ``handle_message`` (the ``awaiting_name`` branch), alongside this call
    rather than inside it. This function remains a harmless, side-effect-free
    call site — e.g. for future observability hooks — and does not itself
    perform any resolution.
    """
    return


def _welcome_message(name: str) -> str:
    """Render the shared post-resolution greeting for ``name``.

    Used identically for the known-number path and the completed
    unknown-number (name-capture) path, so both channels and both
    resolution paths greet a Customer the same way.
    """
    return (
        f"Welcome back, {name}! What can I help with — booking, "
        "browsing services, or checking your appointments?"
    )


async def handle_message(
    db: AsyncSession,
    session_id: str,
    message: str | None,
    *,
    phone_number: str | None = None,
) -> str:
    """Run one Booking Agent turn for ``session_id``.

    - Once the session is ``resolved``, the identity gate no longer applies
      and no further phone-number question is ever asked (AC2).
    - If the session is mid-name-capture (``awaiting_name``), ``message`` is
      treated as the Customer's name: ``find_or_create_customer`` creates the
      ``Customer`` record, and the session is marked resolved with the same
      greeting the known-number path uses (AC3).
    - Otherwise, identity resolution needs a phone number:
        - If the caller (a channel adapter) already knows it, pass it as the
          keyword-only ``phone_number`` — the "ask for phone number" turn is
          skipped entirely and resolution runs immediately against it
          (WhatsApp; FR-3).
        - If not (``phone_number`` is ``None``), no ``message`` yet means the
          opening turn: return the phone-number prompt, without touching
          identity resolution (AC1; Web Chat's unchanged behavior). Once
          ``message`` arrives it is treated as the phone number.
    - A resolved phone number matching an existing ``Customer`` record
      greets the Customer by name and marks the session resolved (AC2); no
      match asks exactly one follow-up question (the Customer's name),
      setting ``awaiting_name`` so the next turn completes resolution (AC3).
    """
    state = session_store.get_or_create(session_id)

    if state.resolved:
        return _ALREADY_RESOLVED_PLACEHOLDER

    if state.awaiting_name:
        if message is None:
            return _NEW_CUSTOMER_INTERIM
        assert state.phone_number is not None
        customer = await find_or_create_customer(db, state.phone_number, message)
        state.customer_id = customer.id
        state.customer_name = customer.name
        state.resolved = True
        state.awaiting_name = False
        session_store.save(session_id, state)
        return _welcome_message(customer.name)

    if phone_number is None:
        if message is None:
            return _ASK_PHONE_NUMBER
        resolved_phone_number = message
    else:
        resolved_phone_number = phone_number

    customer = await resolve_customer_by_phone(db, resolved_phone_number)

    if customer is not None:
        state.phone_number = resolved_phone_number
        state.customer_id = customer.id
        state.customer_name = customer.name
        state.resolved = True
        session_store.save(session_id, state)
        return _welcome_message(customer.name)

    state.phone_number = resolved_phone_number
    state.awaiting_name = True
    session_store.save(session_id, state)
    hand_off_to_new_customer_flow(session_id, resolved_phone_number)
    return _NEW_CUSTOMER_INTERIM


def present_intent_for_verification(intent: BookingIntent) -> VerifiedBookingIntent:
    """Surface a freshly-parsed ``BookingIntent`` for the SM-4a checkpoint (APPOINTMEN-21).

    This is the hook point a future conversational Booking Agent loop will
    call immediately after ``parse_booking_intent``
    (``app.agent.booking_intent``), before staff-preference limiting, an
    actual availability check, or any Story 2.5/2.6/2.7 (FR-6/7/8)
    resolution code runs. Not customer-visible — it logs the parsed intent
    as the observable checkpoint moment and returns an unverified
    ``VerifiedBookingIntent``; a human operator reviews or corrects it and
    sets ``verified`` to ``True`` before
    ``app.domain.booking_intent_verification.require_verified_intent`` will
    let it through.
    """
    _logger.info(
        "SM-4a checkpoint - parsed booking intent awaiting human verification: "
        "service_name=%r requested_time=%r staff_preference=%r",
        intent.service_name,
        intent.requested_time,
        intent.staff_preference,
    )
    return VerifiedBookingIntent(intent=intent)


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


async def present_nearest_alternatives(
    db: AsyncSession,
    *,
    service_name: str,
    requested_time: datetime,
    staff_name: str | None = None,
) -> str:
    """Present the FR-8 nearest-alternative(s) message for an unavailable exact time.

    This is the FR-8 counterpart to ``confirm_exact_match`` (FR-6) — the
    hook point a future conversational Booking Agent loop will call once
    intent parsing (FR-5) and the SM-4a checkpoint have determined the
    Customer's named exact time did not resolve directly. Calls
    ``find_nearest_alternatives`` to resolve the candidate staff set, the
    unavailability reason, and up to two nearest free alternative slots,
    then ``render_alternative_slots`` to turn that into the Customer-facing
    message. Raises ``StaffNotFoundError`` or ``NoAlternativeSlotFoundError``
    exactly as ``find_nearest_alternatives`` does — no wiring into a live
    conversational loop exists yet (see the APPOINTMEN-24 implementation
    plan's Technical Context).
    """
    result = await find_nearest_alternatives(
        db,
        service_name=service_name,
        requested_time=requested_time,
        staff_name=staff_name,
    )
    return render_alternative_slots(result, service_name)


class DaySlotListing(BaseModel):
    """The FR-7 day-only slot listing ready to send to the Customer."""

    day: date
    slots: list[OpenSlot]
    message: str


async def list_day_slots(
    db: AsyncSession, day: date, staff_name: str | None = None
) -> DaySlotListing:
    """List and render a day's open slots for the Customer (FR-7).

    This is the hook point a future conversational Booking Agent loop will
    call once intent parsing has resolved a day-only (no exact time)
    request, exactly the same not-yet-wired-in posture ``confirm_exact_match``
    already has for FR-6. Delegates the actual query/filter logic to
    ``app.domain.availability.list_open_slots_for_day`` and rendering to
    ``render_day_slot_list``, returning both as a ``DaySlotListing`` for that
    future loop to consume.
    """
    slots = await list_open_slots_for_day(db, day, staff_name)
    message = render_day_slot_list(day, slots)
    return DaySlotListing(day=day, slots=slots, message=message)


def present_alternative_for_verification(
    suggestion: AlternativeSlotSuggestion,
) -> VerifiedAlternativeSlotSuggestion:
    """Surface a freshly-produced ``AlternativeSlotSuggestion`` for the SM-4b checkpoint (APPOINTMEN-25).

    This is the hook point a future conversational Booking Agent loop will
    call immediately after ``present_nearest_alternatives``'s Story 2.7/FR-8
    nearest-alternative reasoning, before any "offer alternative to
    customer" step runs. Not customer-visible — it logs the suggestion as
    the observable checkpoint moment and returns an unverified
    ``VerifiedAlternativeSlotSuggestion``; a human operator reviews or
    corrects it and sets ``verified`` to ``True`` before
    ``app.domain.alternative_slot_verification.require_verified_alternative_slot``
    will let it through.
    """
    _logger.info(
        "SM-4b checkpoint - alternative-slot suggestion awaiting human verification: "
        "requested_time=%r unavailable_reason=%r alternative.service_name=%r "
        "alternative.start_time=%r alternative.staff_name=%r",
        suggestion.requested_time,
        suggestion.unavailable_reason,
        suggestion.alternative.service_name,
        suggestion.alternative.start_time,
        suggestion.alternative.staff_name,
    )
    return VerifiedAlternativeSlotSuggestion(suggestion=suggestion)
