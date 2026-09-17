"""Regression test for AC3 (APPOINTMEN-58): no booking/cancel/edit route
exists via ``/dashboard/bookings`` or elsewhere in the API surface.

Locks in the audit finding recorded in
``development/plans/APPOINTMEN-58-implementation-plan.md``: the Dashboard
bookings surface (``app/api/dashboard.py``, ``app/domain/dashboard.py``) is
read-only, and no other registered route exposes a booking mutation for
Dashboard use. Mirrors ``test_staff_no_mutation_path.py``'s route-table +
module-callable-surface pattern, scoped to bookings/dashboard instead of
staff.

``create_booking``/``set_booking_status`` in ``app.repositories.bookings``
are expected and allowed to exist — they are the Booking Agent's own write
path (``app.domain.appointments.confirm_and_create_booking``'s FR-9
confirm-before-write gate), not a Dashboard path. This test asserts they are
never *reachable* (bound as a name) from ``app.api.dashboard`` or
``app.domain.dashboard``, not that they don't exist anywhere in the codebase.
"""

import inspect
from types import ModuleType

from fastapi.routing import APIRoute

from app.api import dashboard as dashboard_api
from app.domain import dashboard as dashboard_domain
from app.main import app
from app.repositories import bookings as bookings_repository

_SAFE_HTTP_METHODS = {"GET", "HEAD", "OPTIONS"}

_MUTATION_VERB_PREFIXES = (
    "create_",
    "add_",
    "update_",
    "edit_",
    "delete_",
    "remove_",
    "set_",
    "cancel_",
)

_ALLOWED_DASHBOARD_DOMAIN_CALLABLES = {
    "get_dashboard_staff_status",
    "get_dashboard_bookings",
}

_MUTATION_REPOSITORY_CALLABLE_NAMES = {"create_booking", "set_booking_status"}


def _public_module_callables(module: ModuleType) -> dict[str, object]:
    """Return public (non-underscore-prefixed) functions defined in ``module``.

    Excludes names imported from elsewhere (e.g. re-exported helpers) so the
    assertion targets only callables the module itself defines.
    """
    return {
        name: obj
        for name, obj in vars(module).items()
        if not name.startswith("_")
        and inspect.isfunction(obj)
        and obj.__module__ == module.__name__
    }


def test_no_non_get_route_mentions_booking_or_dashboard() -> None:
    """No registered FastAPI route with 'booking' or 'dashboard' in its path
    allows any HTTP method beyond GET/HEAD/OPTIONS."""
    offending: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        path = route.path.lower()
        if "booking" not in path and "dashboard" not in path:
            continue
        unsafe_methods = set(route.methods or set()) - _SAFE_HTTP_METHODS
        if unsafe_methods:
            offending.append(f"{sorted(unsafe_methods)} {route.path}")

    assert not offending, (
        "Found booking/dashboard route(s) with non-GET/HEAD/OPTIONS "
        f"method(s), violating AC3 (no booking/cancel/edit route via "
        f"/dashboard or elsewhere): {offending}"
    )


def test_dashboard_domain_module_exposes_only_read_only_aggregation_functions() -> None:
    """app.domain.dashboard must not define any create/update/delete callable."""
    public_callables = _public_module_callables(dashboard_domain)

    unexpected = set(public_callables) - _ALLOWED_DASHBOARD_DOMAIN_CALLABLES
    assert not unexpected, (
        "app.domain.dashboard defines unexpected public callable(s) beyond "
        f"the known read-only aggregation functions, violating AC3: "
        f"{sorted(unexpected)}"
    )

    mutation_named = [
        name for name in public_callables if name.startswith(_MUTATION_VERB_PREFIXES)
    ]
    assert not mutation_named, (
        "app.domain.dashboard defines callable(s) with a mutation-verb "
        f"name, violating AC3 (no Dashboard bookings mutation path): "
        f"{mutation_named}"
    )


def test_dashboard_api_module_registers_only_get_route_handlers() -> None:
    """Every route whose handler is defined in app.api.dashboard is GET-only."""
    offending: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.endpoint.__module__ != dashboard_api.__name__:
            continue
        unsafe_methods = set(route.methods or set()) - _SAFE_HTTP_METHODS
        if unsafe_methods:
            offending.append(f"{sorted(unsafe_methods)} {route.path}")

    assert not offending, (
        "app.api.dashboard registers route(s) with non-GET/HEAD/OPTIONS "
        f"method(s), violating AC3: {offending}"
    )


def test_dashboard_surface_never_binds_a_booking_mutation_function() -> None:
    """create_booking/set_booking_status must never be bound names reachable
    from the Dashboard bookings surface.

    Importing a function into a module's namespace is a prerequisite for
    calling it in plain Python, so checking the absence of these names from
    ``vars(module)`` is a mechanical proxy for "never called from
    app.api.dashboard or app.domain.dashboard".
    """
    for module in (dashboard_api, dashboard_domain):
        bound_names = set(vars(module))
        leaked = bound_names & _MUTATION_REPOSITORY_CALLABLE_NAMES
        assert not leaked, (
            f"{module.__name__} binds mutation callable(s) {sorted(leaked)} "
            "from app.repositories.bookings, violating AC3 (Dashboard "
            "bookings surface must stay read-only)"
        )

    # Sanity check the assumption above so this test is not vacuously true:
    # the mutation callables really do exist in app.repositories.bookings,
    # just not reachable from the Dashboard surface.
    for name in _MUTATION_REPOSITORY_CALLABLE_NAMES:
        assert hasattr(bookings_repository, name), (
            f"expected app.repositories.bookings.{name} to exist — if it "
            "was renamed or removed, this test's assumptions need updating"
        )
