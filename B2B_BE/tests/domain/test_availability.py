from datetime import UTC, datetime

from app.domain.availability import _is_blocked_at
from app.models.availability import Availability


def _row(
    *, start_time: datetime, end_time: datetime, blocked: bool, created_at: datetime
) -> Availability:
    """Build an in-memory Availability row, no DB required."""
    return Availability(
        start_time=start_time,
        end_time=end_time,
        blocked=blocked,
        created_at=created_at,
    )


def test_is_blocked_at_returns_false_with_no_covering_row() -> None:
    now = datetime(2026, 9, 17, 10, 0, tzinfo=UTC)
    rows = [
        _row(
            start_time=datetime(2026, 9, 17, 12, 0, tzinfo=UTC),
            end_time=datetime(2026, 9, 17, 13, 0, tzinfo=UTC),
            blocked=True,
            created_at=datetime(2026, 9, 17, 8, 0, tzinfo=UTC),
        )
    ]

    assert _is_blocked_at(rows, now) is False


def test_is_blocked_at_returns_true_when_covering_row_is_blocked() -> None:
    now = datetime(2026, 9, 17, 10, 30, tzinfo=UTC)
    rows = [
        _row(
            start_time=datetime(2026, 9, 17, 10, 0, tzinfo=UTC),
            end_time=datetime(2026, 9, 17, 11, 0, tzinfo=UTC),
            blocked=True,
            created_at=datetime(2026, 9, 17, 8, 0, tzinfo=UTC),
        )
    ]

    assert _is_blocked_at(rows, now) is True


def test_is_blocked_at_returns_false_when_covering_row_is_unblocked() -> None:
    now = datetime(2026, 9, 17, 10, 30, tzinfo=UTC)
    rows = [
        _row(
            start_time=datetime(2026, 9, 17, 10, 0, tzinfo=UTC),
            end_time=datetime(2026, 9, 17, 11, 0, tzinfo=UTC),
            blocked=False,
            created_at=datetime(2026, 9, 17, 8, 0, tzinfo=UTC),
        )
    ]

    assert _is_blocked_at(rows, now) is False


def test_is_blocked_at_uses_latest_created_covering_row() -> None:
    """When two rows both cover ``now``, the most-recently-created wins."""
    now = datetime(2026, 9, 17, 10, 30, tzinfo=UTC)
    older_block = _row(
        start_time=datetime(2026, 9, 17, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 9, 17, 11, 0, tzinfo=UTC),
        blocked=True,
        created_at=datetime(2026, 9, 17, 8, 0, tzinfo=UTC),
    )
    newer_unblock = _row(
        start_time=datetime(2026, 9, 17, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 9, 17, 11, 0, tzinfo=UTC),
        blocked=False,
        created_at=datetime(2026, 9, 17, 9, 0, tzinfo=UTC),
    )

    assert _is_blocked_at([older_block, newer_unblock], now) is False


def test_is_blocked_at_ignores_non_covering_boundary_instants() -> None:
    """A row's window is [start_time, end_time) — end_time itself is exclusive."""
    end_time = datetime(2026, 9, 17, 11, 0, tzinfo=UTC)
    rows = [
        _row(
            start_time=datetime(2026, 9, 17, 10, 0, tzinfo=UTC),
            end_time=end_time,
            blocked=True,
            created_at=datetime(2026, 9, 17, 8, 0, tzinfo=UTC),
        )
    ]

    assert _is_blocked_at(rows, end_time) is False
