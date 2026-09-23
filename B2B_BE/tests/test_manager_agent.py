from unittest.mock import AsyncMock, patch

import pytest

from app.agent.manager_agent import (
    _STAFF_CATALOG_BOUNDARY_REDIRECT,
    SpeakerContext,
    handle_staff_catalog_boundary,
)
from app.models.staff import StaffRole


def _speaker(role: StaffRole, *, id: int = 1, name: str = "Meena") -> SpeakerContext:
    return SpeakerContext(id=id, name=name, role=role)


@pytest.mark.asyncio
async def test_handle_staff_catalog_boundary_redirects_staff_catalog_change_request() -> None:
    speaker = _speaker(StaffRole.STAFF)

    with patch(
        "app.agent.manager_agent.is_catalog_change_request", AsyncMock(return_value=True)
    ):
        result = await handle_staff_catalog_boundary(speaker, "add beard trim for 150 rupees")

    assert result == "That's something Ramesh manages — I can help you with your own availability."
    assert result == _STAFF_CATALOG_BOUNDARY_REDIRECT


@pytest.mark.asyncio
async def test_handle_staff_catalog_boundary_never_redirects_owner_admin() -> None:
    speaker = _speaker(StaffRole.OWNER_ADMIN, name="Ramesh")

    with patch(
        "app.agent.manager_agent.is_catalog_change_request", AsyncMock(return_value=True)
    ):
        result = await handle_staff_catalog_boundary(speaker, "add beard trim for 150 rupees")

    assert result is None


@pytest.mark.asyncio
async def test_handle_staff_catalog_boundary_returns_none_for_non_catalog_staff_message() -> None:
    speaker = _speaker(StaffRole.STAFF)

    with patch(
        "app.agent.manager_agent.is_catalog_change_request", AsyncMock(return_value=False)
    ):
        result = await handle_staff_catalog_boundary(speaker, "block out Friday morning")

    assert result is None
