"""Regression test for FR-22: no Staff mutation path exists anywhere in B2B_BE/.

Locks in the audit finding recorded in
``development/plans/APPOINTMEN-42-implementation-plan.md``: the Staff table is
view-only for this demo. If a future change introduces a Staff create/update/
delete tool, route, or repository function, this test fails loudly and names
the offending symbol, forcing deliberate review instead of silent drift.
"""

import inspect
from types import ModuleType

from fastapi.routing import APIRoute

from app.main import app
from app.tools import staff as staff_tools
from app.repositories import staff_repository

_SAFE_HTTP_METHODS = {"GET", "HEAD", "OPTIONS"}

_MUTATION_VERB_PREFIXES = ("create_", "add_", "update_", "edit_", "delete_", "remove_")

_ALLOWED_STAFF_TOOL_CALLABLES = {"resolve_staff_identity"}

_ALLOWED_STAFF_REPOSITORY_CALLABLES = {
    "get_staff_by_phone_number",
    "get_staff_by_name",
}


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


def test_no_non_get_route_mentions_staff() -> None:
    """No registered FastAPI route with 'staff' in its path allows mutation."""
    offending: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if "staff" not in route.path.lower():
            continue
        unsafe_methods = set(route.methods or set()) - _SAFE_HTTP_METHODS
        if unsafe_methods:
            offending.append(f"{sorted(unsafe_methods)} {route.path}")

    assert not offending, (
        "Found staff route(s) with non-GET/HEAD/OPTIONS method(s), violating "
        f"FR-22 (no Staff mutation path): {offending}"
    )


def test_staff_tools_expose_only_read_only_identity_resolution() -> None:
    """app.tools.staff must not define any create/update/delete callable."""
    public_callables = _public_module_callables(staff_tools)

    unexpected = set(public_callables) - _ALLOWED_STAFF_TOOL_CALLABLES
    assert not unexpected, (
        "app.tools.staff defines unexpected public callable(s) beyond "
        f"resolve_staff_identity, violating FR-22: {sorted(unexpected)}"
    )

    mutation_named = [
        name
        for name in public_callables
        if name.startswith(_MUTATION_VERB_PREFIXES)
    ]
    assert not mutation_named, (
        "app.tools.staff defines callable(s) with a mutation-verb name, "
        f"violating FR-22 (no Staff mutation path): {mutation_named}"
    )


def test_staff_repository_exposes_only_known_read_functions() -> None:
    """app.repositories.staff_repository must expose only the two read functions."""
    public_callables = _public_module_callables(staff_repository)

    unexpected = set(public_callables) - _ALLOWED_STAFF_REPOSITORY_CALLABLES
    assert not unexpected, (
        "app.repositories.staff_repository defines unexpected public "
        f"callable(s) beyond the known read-only functions, violating "
        f"FR-22 (no Staff mutation path): {sorted(unexpected)}"
    )

    mutation_named = [
        name
        for name in public_callables
        if name.startswith(_MUTATION_VERB_PREFIXES)
    ]
    assert not mutation_named, (
        "app.repositories.staff_repository defines callable(s) with a "
        f"mutation-verb name, violating FR-22 (no Staff mutation path): "
        f"{mutation_named}"
    )
