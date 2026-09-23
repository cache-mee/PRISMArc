from datetime import datetime

from app.agent.booking_intent import BookingIntent
from app.agent.state import pending_verification_store
from app.domain.alternative_slot_verification import (
    AlternativeSlotSuggestion,
    VerifiedAlternativeSlotSuggestion,
)
from app.domain.appointments import ResolvedBookingCandidate
from app.domain.booking_intent_verification import VerifiedBookingIntent
from app.domain.conflict_verification import VerifiedConflictCheck
from app.domain.conflicts import ConflictCheckResult


def _make_verified_booking_intent(service_name: str = "Haircut") -> VerifiedBookingIntent:
    return VerifiedBookingIntent(
        intent=BookingIntent(service_name=service_name), verified=False
    )


def _make_verified_alternative_slot() -> VerifiedAlternativeSlotSuggestion:
    return VerifiedAlternativeSlotSuggestion(
        suggestion=AlternativeSlotSuggestion(
            requested_time=datetime(2026, 9, 18, 9, 0),
            unavailable_reason="Requested slot already booked",
            alternative=ResolvedBookingCandidate(
                service_name="Haircut",
                start_time=datetime(2026, 9, 18, 10, 0),
                staff_name="Dr. Rao",
            ),
        ),
        verified=False,
    )


def _make_verified_conflict_check() -> VerifiedConflictCheck:
    return VerifiedConflictCheck(
        result=ConflictCheckResult(has_conflict=False, conflicting_bookings=[]),
        verified=False,
    )


def test_get_pending_booking_intent_returns_none_when_unset() -> None:
    pending_verification_store.set_pending_booking_intent(None)

    assert pending_verification_store.get_pending_booking_intent() is None


def test_set_and_get_pending_booking_intent_round_trips_exact_object() -> None:
    pending = _make_verified_booking_intent()

    pending_verification_store.set_pending_booking_intent(pending)

    assert pending_verification_store.get_pending_booking_intent() == pending


def test_set_pending_booking_intent_overwrites_previous_value() -> None:
    first = _make_verified_booking_intent("Haircut")
    second = _make_verified_booking_intent("Manicure")

    pending_verification_store.set_pending_booking_intent(first)
    pending_verification_store.set_pending_booking_intent(second)

    assert pending_verification_store.get_pending_booking_intent() == second


def test_get_pending_alternative_slot_returns_none_when_unset() -> None:
    pending_verification_store.set_pending_alternative_slot(None)

    assert pending_verification_store.get_pending_alternative_slot() is None


def test_set_and_get_pending_alternative_slot_round_trips_exact_object() -> None:
    pending = _make_verified_alternative_slot()

    pending_verification_store.set_pending_alternative_slot(pending)

    assert pending_verification_store.get_pending_alternative_slot() == pending


def test_set_pending_alternative_slot_overwrites_previous_value() -> None:
    first = _make_verified_alternative_slot()
    second = _make_verified_alternative_slot()
    second.suggestion.unavailable_reason = "Staff on leave"

    pending_verification_store.set_pending_alternative_slot(first)
    pending_verification_store.set_pending_alternative_slot(second)

    assert pending_verification_store.get_pending_alternative_slot() == second


def test_get_pending_conflict_check_returns_none_when_unset() -> None:
    pending_verification_store.set_pending_conflict_check(None)

    assert pending_verification_store.get_pending_conflict_check() is None


def test_set_and_get_pending_conflict_check_round_trips_exact_object() -> None:
    pending = _make_verified_conflict_check()

    pending_verification_store.set_pending_conflict_check(pending)

    assert pending_verification_store.get_pending_conflict_check() == pending


def test_set_pending_conflict_check_overwrites_previous_value() -> None:
    first = _make_verified_conflict_check()
    second = VerifiedConflictCheck(
        result=ConflictCheckResult(has_conflict=True, conflicting_bookings=[]),
        verified=True,
    )

    pending_verification_store.set_pending_conflict_check(first)
    pending_verification_store.set_pending_conflict_check(second)

    assert pending_verification_store.get_pending_conflict_check() == second
