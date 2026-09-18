import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.manager_agent import SpeakerContext
from app.agent.state import session_store
from app.domain.availability import ProposedAvailabilityChange
from app.models.availability import Availability
from app.models.staff import StaffRole
from app.tools.availability_change import (
    ConfirmAvailabilityChangeArgs,
    NoPendingAvailabilityChangeError,
    ProposeAvailabilityChangeArgs,
    confirm_availability_change,
    propose_availability_change,
)

STAFF_SPEAKER = SpeakerContext(id=1, name="Dr. Rao", role=StaffRole.STAFF)
OWNER_ADMIN_SPEAKER = SpeakerContext(id=2, name="Ramesh", role=StaffRole.OWNER_ADMIN)

_PARSED_CHANGE = ProposedAvailabilityChange(
    staff_name="Dr. Rao",
    start_time=datetime(2026, 9, 18, 9, 0),
    end_time=datetime(2026, 9, 18, 13, 0),
    blocked=True,
    confirmed=False,
)


def _unique_session_id() -> str:
    return f"session-{uuid.uuid4()}"


@pytest.mark.asyncio
async def test_propose_availability_change_stores_pending_change_and_returns_restatement() -> None:
    session_id = _unique_session_id()

    result = await propose_availability_change(
        session_id,
        STAFF_SPEAKER,
        ProposeAvailabilityChangeArgs(
            start_time=_PARSED_CHANGE.start_time,
            end_time=_PARSED_CHANGE.end_time,
            blocked=_PARSED_CHANGE.blocked,
        ),
    )

    state = session_store.get_or_create(session_id)
    assert state.pending_availability_change == _PARSED_CHANGE
    assert result["declined"] is False
    assert "restatement" in result
    assert "Dr. Rao" in result["restatement"]


@pytest.mark.asyncio
async def test_propose_availability_change_declines_for_owner_admin_without_storing() -> None:
    session_id = _unique_session_id()

    result = await propose_availability_change(
        session_id,
        OWNER_ADMIN_SPEAKER,
        ProposeAvailabilityChangeArgs(
            start_time=_PARSED_CHANGE.start_time,
            end_time=_PARSED_CHANGE.end_time,
            blocked=_PARSED_CHANGE.blocked,
        ),
    )

    state = session_store.get_or_create(session_id)
    assert result["declined"] is True
    assert state.pending_availability_change is None


@pytest.mark.asyncio
async def test_confirm_availability_change_true_applies_and_clears_pending() -> None:
    session_id = _unique_session_id()
    state = session_store.get_or_create(session_id)
    state.pending_availability_change = _PARSED_CHANGE
    session_store.save(session_id, state)

    applied_row = Availability(
        id=42,
        staff_id=1,
        start_time=_PARSED_CHANGE.start_time,
        end_time=_PARSED_CHANGE.end_time,
        blocked=_PARSED_CHANGE.blocked,
    )
    domain_mock = AsyncMock(return_value=applied_row)

    with patch(
        "app.tools.availability_change.confirm_and_apply_availability_change",
        domain_mock,
    ):
        result = await confirm_availability_change(
            db=AsyncMock(),
            session_id=session_id,
            speaker=STAFF_SPEAKER,
            args=ConfirmAvailabilityChangeArgs(confirmed=True),
        )

    domain_mock.assert_called_once()
    called_change = domain_mock.call_args.args[1]
    assert called_change.confirmed is True
    assert called_change.staff_name == _PARSED_CHANGE.staff_name

    assert result["confirmed"] is True
    assert result["applied"] is True
    assert result["availability_id"] == 42

    reloaded = session_store.get_or_create(session_id)
    assert reloaded.pending_availability_change is None


@pytest.mark.asyncio
async def test_confirm_availability_change_false_never_calls_domain_and_clears_pending() -> None:
    session_id = _unique_session_id()
    state = session_store.get_or_create(session_id)
    state.pending_availability_change = _PARSED_CHANGE
    session_store.save(session_id, state)

    domain_mock = AsyncMock()

    with patch(
        "app.tools.availability_change.confirm_and_apply_availability_change",
        domain_mock,
    ):
        result = await confirm_availability_change(
            db=AsyncMock(),
            session_id=session_id,
            speaker=STAFF_SPEAKER,
            args=ConfirmAvailabilityChangeArgs(confirmed=False),
        )

    domain_mock.assert_not_called()
    assert result["confirmed"] is False
    assert result["applied"] is False

    reloaded = session_store.get_or_create(session_id)
    assert reloaded.pending_availability_change is None


@pytest.mark.asyncio
async def test_confirm_availability_change_raises_when_nothing_pending() -> None:
    session_id = _unique_session_id()
    domain_mock = AsyncMock()

    with patch(
        "app.tools.availability_change.confirm_and_apply_availability_change",
        domain_mock,
    ):
        with pytest.raises(NoPendingAvailabilityChangeError):
            await confirm_availability_change(
                db=AsyncMock(),
                session_id=session_id,
                speaker=STAFF_SPEAKER,
                args=ConfirmAvailabilityChangeArgs(confirmed=True),
            )

    domain_mock.assert_not_called()


@pytest.mark.asyncio
async def test_confirm_availability_change_declines_for_owner_admin_guard() -> None:
    session_id = _unique_session_id()
    owner_admin_pending = ProposedAvailabilityChange(
        staff_name="Ramesh",
        start_time=datetime(2026, 9, 18, 9, 0),
        end_time=datetime(2026, 9, 18, 13, 0),
        blocked=True,
        confirmed=False,
    )
    state = session_store.get_or_create(session_id)
    state.pending_availability_change = owner_admin_pending
    session_store.save(session_id, state)

    domain_mock = AsyncMock()

    with patch(
        "app.tools.availability_change.confirm_and_apply_availability_change",
        domain_mock,
    ):
        result = await confirm_availability_change(
            db=AsyncMock(),
            session_id=session_id,
            speaker=OWNER_ADMIN_SPEAKER,
            args=ConfirmAvailabilityChangeArgs(confirmed=True),
        )

    domain_mock.assert_not_called()
    assert result["declined"] is True
