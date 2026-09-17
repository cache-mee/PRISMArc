import pytest

from app.domain.conflict_verification import VerifiedConflictCheck
from app.domain.conflicts import ConflictCheckResult, ConflictingBooking
from app.tools.conflict_verification import VerifyConflictCheckArgs, verify_conflict_check

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
def test_verify_conflict_check_true_marks_verified(result: ConflictCheckResult) -> None:
    pending = VerifiedConflictCheck(result=result)

    verified_check = verify_conflict_check(pending, VerifyConflictCheckArgs(verified=True))

    assert isinstance(verified_check, VerifiedConflictCheck)
    assert verified_check.verified is True
    assert verified_check.result == pending.result


@pytest.mark.parametrize("result", [NO_CONFLICT_RESULT, HAS_CONFLICT_RESULT])
def test_verify_conflict_check_false_records_decline(result: ConflictCheckResult) -> None:
    pending = VerifiedConflictCheck(result=result)

    verified_check = verify_conflict_check(pending, VerifyConflictCheckArgs(verified=False))

    assert verified_check.verified is False
    assert verified_check.result == pending.result
