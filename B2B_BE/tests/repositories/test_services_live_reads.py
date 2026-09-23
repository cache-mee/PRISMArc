"""FR-31 (APPOINTMEN-46) regression coverage: a confirmed catalog/price edit
is visible on the very next catalog read — never a stale, once-fetched
snapshot.

Exercises the real repository read path (``list_services``) against a real
``AsyncSession``, in two scenarios:

- The actual production shape: every conversation turn is a separate HTTP
  request, and ``app.database.get_db`` hands each one a brand-new
  ``AsyncSession`` (mirrored here by a fresh session per "turn"). This
  already passed before this ticket's change — nothing here was ever
  reachably broken under real request wiring.
- A single ``AsyncSession`` reused across both "turns", with the first
  read's rows still held (a caller that keeps its previously-fetched
  catalog around, e.g. across conversation turns, rather than discarding it
  immediately) — a strictly harder case than production wiring, but one
  ``update_service``/``deactivate_service`` make possible in principle,
  since both mutate an existing ``Service`` row in place rather than
  inserting a new one (unlike Availability, which never updates a row in
  place — see ``test_availability_live_reads.py``). Without
  ``list_services``'s ``populate_existing=True`` (this ticket's fix),
  SQLAlchemy's identity map would keep re-handing back that first,
  now-stale, pre-edit ``Service`` object on the second read instead of a
  fresh one reflecting the confirmed price change.
"""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.services import ProposedServiceEdit, confirm_and_update_service
from app.models.service import Service
from app.repositories.services import list_services

pytestmark = pytest.mark.asyncio

_TODAY = date(2026, 9, 21)


async def _seed_service(session_factory: async_sessionmaker[AsyncSession]) -> int:
    async with session_factory() as db:
        service = Service(name="Haircut", price=300)
        db.add(service)
        await db.commit()
        await db.refresh(service)
        return service.id


async def _catalog_prices(db: AsyncSession) -> dict[str, float]:
    services = await list_services(db)
    return {service.name: float(service.price) for service in services}


async def test_price_change_on_a_fresh_session_is_reflected_on_the_next_browse(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """Mirrors production wiring: each conversation turn gets its own session."""
    service_id = await _seed_service(db_sessionmaker)

    async with db_sessionmaker() as first_browse_db:
        assert (await _catalog_prices(first_browse_db))["Haircut"] == 300

    async with db_sessionmaker() as edit_db:
        await confirm_and_update_service(
            edit_db,
            ProposedServiceEdit(service_id=service_id, new_price=350, confirmed=True),
        )

    async with db_sessionmaker() as next_browse_db:
        assert (await _catalog_prices(next_browse_db))["Haircut"] == 350


async def test_price_change_is_reflected_even_on_a_session_reused_across_browses(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """The harder, session-reuse case this ticket's ``populate_existing`` fix closes.

    ``first_read`` is kept alive (not just its price) across the edit, so
    ``reused_db``'s identity map genuinely still holds that first-loaded
    ``Service`` row when the second read runs — this is what would let a
    naive re-read return the pre-edit price without
    ``populate_existing=True`` on ``list_services``: SQLAlchemy's identity
    map does not overwrite an already-loaded object's attributes from a
    later query by default, only when something has evicted it first (e.g.
    garbage collection once nothing still references it, which is not the
    case here).
    """
    service_id = await _seed_service(db_sessionmaker)

    async with db_sessionmaker() as reused_db:
        first_read = await list_services(reused_db)
        assert {s.name: float(s.price) for s in first_read}["Haircut"] == 300

        async with db_sessionmaker() as edit_db:
            await confirm_and_update_service(
                edit_db,
                ProposedServiceEdit(
                    service_id=service_id, new_price=350, confirmed=True
                ),
            )

        second_read = await list_services(reused_db)
        assert {s.name: float(s.price) for s in second_read}["Haircut"] == 350
        # first_read is kept alive up to here so it cannot be garbage
        # collected out of reused_db's identity map before second_read runs.
        assert first_read[0] is second_read[0]
        assert float(first_read[0].price) == 350
