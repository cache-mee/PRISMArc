import logging

import pytest

from app.agent.manager_agent import present_conflict_check_for_verification
from app.domain.conflict_verification import VerifiedConflictCheck
from app.domain.conflicts import ConflictCheckResult, ConflictingBooking

NO_CONFLICT_RESULT = ConflictCheckResult(has_conflict=False, conflicting_bookings=[])

HAS_CONFLICT_RESULT = ConflictCheckResult(
    has_conflict=True,
    conflicting_bookings=[
        ConflictingBooking(
            booking_id=1,
            start_time="2026-09-17T10:00:00",
            service_name="Haircut",
        )
    ],
)


@pytest.mark.parametrize("result", [NO_CONFLICT_RESULT, HAS_CONFLICT_RESULT])
def test_present_conflict_check_for_verification_returns_unverified_wrapper(
    result: ConflictCheckResult,
) -> None:
    verified_check = present_conflict_check_for_verification(result)

    assert isinstance(verified_check, VerifiedConflictCheck)
    assert verified_check.result == result
    assert verified_check.verified is False


@pytest.mark.parametrize("result", [NO_CONFLICT_RESULT, HAS_CONFLICT_RESULT])
def test_present_conflict_check_for_verification_logs_outcome(
    caplog: pytest.LogCaptureFixture, result: ConflictCheckResult
) -> None:
    with caplog.at_level(logging.INFO, logger="app.agent.manager_agent"):
        present_conflict_check_for_verification(result)

    info_records = [record for record in caplog.records if record.levelno == logging.INFO]
    assert len(info_records) == 1
    message = info_records[0].getMessage()
    assert f"has_conflict={result.has_conflict!r}" in message
    for booking in result.conflicting_bookings:
        assert str(booking.booking_id) in message
        assert repr(booking.start_time) in message
