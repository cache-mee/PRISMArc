import pytest

from app.domain.conflict_verification import (
    ConflictCheckNotVerifiedError,
    VerifiedConflictCheck,
    require_verified_conflict_check,
)
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
def test_require_verified_conflict_check_raises_when_unverified(
    result: ConflictCheckResult,
) -> None:
    verified_check = VerifiedConflictCheck(result=result)

    with pytest.raises(ConflictCheckNotVerifiedError):
        require_verified_conflict_check(verified_check)


@pytest.mark.parametrize("result", [NO_CONFLICT_RESULT, HAS_CONFLICT_RESULT])
def test_require_verified_conflict_check_returns_result_when_verified(
    result: ConflictCheckResult,
) -> None:
    verified_check = VerifiedConflictCheck(result=result, verified=True)

    returned = require_verified_conflict_check(verified_check)

    assert returned == result
