"""FR-31 (APPOINTMEN-46) regression coverage: a confirmed staff block is
visible on the very next slot read — never a stale, once-fetched snapshot.

Exercises the real repository/domain read path (``list_open_slots_for_day``)
against a real ``AsyncSession``, in two scenarios:

- The actual production shape: every conversation turn is a separate HTTP
  request, and ``app.database.get_db`` hands each one a brand-new
  ``AsyncSession`` (mirrored here by a fresh session per "turn").
- A single ``AsyncSession`` reused across both "turns" — a strictly harder
  case than production wiring. It already passes with no production-code
  change: blocking/unblocking (``confirm_and_apply_availability_change``)
  only ever *inserts* a new ``Availability`` row
  (``app.repositories.availability.create_availability`` is documented as
  "the sole insert path"; there is no update/delete path for this table), so
  a block made mid-conversation is always a brand-new primary key that
  cannot already be sitting stale in a session's identity map. This test
  locks that guarantee in.
"""

from datetime import date, datetime, time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.availability import (
    ProposedAvailabilityChange,
    confirm_and_apply_availability_change,
    list_open_slots_for_day,
)
from app.models.staff import Staff, StaffRole

pytestmark = pytest.mark.asyncio

# Naive datetimes, matching app.domain.availability._generate_slot_grid's own
# datetime.combine(day, time) convention (no tzinfo) for the salon's slot grid.
_DAY = date(2026, 9, 21)
_BLOCK_START = datetime.combine(_DAY, time(10, 0))
_BLOCK_END = datetime.combine(_DAY, time(11, 0))


async def _seed_staff(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as db:
        db.add(Staff(name="Meena", phone_number="+10000000001", role=StaffRole.STAFF))
        await db.commit()


async def _open_slot_starts(
    db: AsyncSession, staff_name: str = "Meena"
) -> list[datetime]:
    slots = await list_open_slots_for_day(db, _DAY, staff_name)
    return [slot.start_time for slot in slots]


async def test_staff_block_on_a_fresh_session_is_not_offered_on_the_next_turn(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """Mirrors production wiring: each conversation turn gets its own session."""
    await _seed_staff(db_sessionmaker)

    async with db_sessionmaker() as first_turn_db:
        assert _BLOCK_START in await _open_slot_starts(first_turn_db)

    async with db_sessionmaker() as block_db:
        await confirm_and_apply_availability_change(
            block_db,
            ProposedAvailabilityChange(
                staff_name="Meena",
                start_time=_BLOCK_START,
                end_time=_BLOCK_END,
                blocked=True,
                confirmed=True,
            ),
        )

    async with db_sessionmaker() as next_turn_db:
        assert _BLOCK_START not in await _open_slot_starts(next_turn_db)


async def test_staff_block_is_visible_even_on_a_session_reused_across_turns(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """A stricter case than production wiring: one session spans both turns.

    Still passes with no production-code change, because blocking only ever
    inserts a new ``Availability`` row — there is nothing already sitting in
    ``reused_db``'s identity map for a row that did not exist yet.
    """
    await _seed_staff(db_sessionmaker)

    async with db_sessionmaker() as reused_db:
        assert _BLOCK_START in await _open_slot_starts(reused_db)

        async with db_sessionmaker() as block_db:
            await confirm_and_apply_availability_change(
                block_db,
                ProposedAvailabilityChange(
                    staff_name="Meena",
                    start_time=_BLOCK_START,
                    end_time=_BLOCK_END,
                    blocked=True,
                    confirmed=True,
                ),
            )

        assert _BLOCK_START not in await _open_slot_starts(reused_db)
