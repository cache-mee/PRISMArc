"""Integration test proving AC2 (APPOINTMEN-58): the Shared Data Store
guarantee for GET /dashboard/bookings.

A booking written via ``app.repositories.bookings.create_booking`` (the same
function the Booking Agent's FR-9 confirm-before-write gate,
``app.domain.appointments.confirm_and_create_booking``, calls) must be
returned by ``app.domain.dashboard.get_dashboard_bookings`` on the very next
call, in a separate session, with no intervening cache-clear or refresh step.
A mock cannot disprove the presence of a cache/snapshot layer between the
write and read paths, so this needs a real Postgres connection, per
``base-rules.md``'s stated preference for this class of DB-ordering claim
(see ``development/plans/APPOINTMEN-58-implementation-plan.md``, Task 4).

Uses the project's own ``app.database`` engine/``DATABASE_URL`` wiring — no
new test-only database dependency is introduced. Mirrors
``tests/integration/test_health_container.py``'s convention of *skipping*
(not failing, not faking a pass) when the infrastructure a test depends on
is not reachable in the current execution environment.

In this repo, ``.env`` (symlinked into every ticket worktree by the
``worktree-add`` tool) points ``DATABASE_URL`` at the team's real shared RDS
instance rather than a local Postgres — so "unreachable" here typically means
"no network route to RDS from this sandbox/CI runner," not "nothing is
listening on localhost." That distinction matters: an ``asyncio.wait_for``
wrapped around the async driver's connect coroutine is not sufficient to
bound this, because DNS resolution / the initial TCP handshake attempt for a
genuinely unreachable host blocks the single-threaded asyncio event loop at
the OS/driver level, which prevents ``wait_for``'s own timer from ever firing
(reproduced directly: with that approach, a plain ``pytest`` invocation of
this file — even ``--collect-only`` — hung indefinitely instead of failing
after the configured timeout). The reachability probe below instead does a
synchronous, OS-timeout-bounded raw TCP connect (``socket.create_connection``
with a real ``timeout=`` argument, which the OS enforces even when DNS
resolution itself is slow) to the host/port parsed out of ``DATABASE_URL``,
*before* ever touching the async SQLAlchemy engine — only once that plain
socket connects does the test proceed to the actual (fast, by then) async DB
round trip.
"""

import socket
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.config import settings
from app.database import SessionLocal
from app.domain.dashboard import get_dashboard_bookings
from app.models.customer import Customer
from app.models.staff import Staff
from app.repositories.bookings import create_booking

_SEED_CUSTOMER_PHONE_NUMBER = "+15559999999"
_REACHABILITY_TIMEOUT_SECONDS = 2.0
_DEFAULT_POSTGRES_PORT = 5432


def _postgres_reachable() -> bool:
    """Synchronous, OS-timeout-bounded TCP reachability pre-check.

    Deliberately does not use asyncio/SQLAlchemy at all here — see the
    module docstring for why an async wait_for is not sufficient to bound
    an unreachable-host connect attempt on this project's real RDS-backed
    DATABASE_URL.
    """
    if not settings.database_url:
        return False
    try:
        url = make_url(settings.database_url)
    except Exception:  # noqa: BLE001 - a malformed URL means "not usable"
        return False
    if not url.host:
        return False
    port = url.port or _DEFAULT_POSTGRES_PORT
    try:
        with socket.create_connection((url.host, port), timeout=_REACHABILITY_TIMEOUT_SECONDS):
            return True
    except OSError:
        # Any failure to establish the raw TCP connection (DNS failure,
        # connection refused, timeout, network unreachable, ...) means
        # "not reachable" for this preflight check.
        return False


async def _get_or_create_test_customer(db) -> Customer:
    """Reuse a dedicated test Customer row across runs instead of inserting
    a fresh one every time (keeps the test idempotent under repeated runs
    against the same database)."""
    result = await db.execute(
        select(Customer).where(Customer.phone_number == _SEED_CUSTOMER_PHONE_NUMBER)
    )
    customer = result.scalars().first()
    if customer is not None:
        return customer

    customer = Customer(
        phone_number=_SEED_CUSTOMER_PHONE_NUMBER,
        name="APPOINTMEN-58 Shared Data Store Test Customer",
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


async def test_booking_written_via_create_booking_is_visible_to_get_dashboard_bookings() -> None:
    """AC2's Shared Data Store proof: write via create_booking, read via
    get_dashboard_bookings in a separate call, assert presence."""
    if not _postgres_reachable():
        pytest.skip(
            "not validated — no live Postgres reachable via DATABASE_URL "
            "in this environment (see APPOINTMEN-58 implementation plan, "
            "Task 4 and Risks table)"
        )

    unique_service_name = f"APPOINTMEN-58 Shared Data Store Proof {uuid.uuid4().hex[:8]}"
    start_time = datetime.now(UTC).replace(microsecond=0)

    # Write path: the same repository function
    # app.domain.appointments.confirm_and_create_booking (the Booking
    # Agent's FR-9 write gate) calls.
    async with SessionLocal() as write_db:
        staff_result = await write_db.execute(select(Staff).limit(1))
        staff = staff_result.scalars().first()
        assert staff is not None, (
            "no seeded Staff row found — expected at least one row from the "
            "8aac3e937d39_seed_staff_records migration"
        )
        customer = await _get_or_create_test_customer(write_db)

        await create_booking(
            write_db,
            customer_id=customer.id,
            staff_id=staff.id,
            service_name=unique_service_name,
            start_time=start_time,
        )

    # Read path: a fresh session/call, exactly as the Dashboard's next load
    # would perform it — no cache-clear, refresh call, or other intervening
    # action.
    async with SessionLocal() as read_db:
        entries = await get_dashboard_bookings(read_db, "today")

    matching = [
        entry
        for entry in entries
        if entry.service_name == unique_service_name
    ]
    assert matching, (
        "booking inserted via create_booking was not returned by "
        "get_dashboard_bookings on the very next call — Shared Data Store "
        "guarantee (AC2) violated"
    )
    assert matching[0].staff_name == staff.name
    assert matching[0].customer_name == customer.name
    assert matching[0].start_time == start_time
