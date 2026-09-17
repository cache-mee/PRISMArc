from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.agent.catalog_intent import is_catalog_change_request


def _mock_response(is_catalog_change: bool) -> SimpleNamespace:
    """Builds a fake Anthropic ``messages.create`` response carrying a forced tool-use block,
    matching the shape ``is_catalog_change_request`` reads (``response.content`` containing a
    ``type="tool_use"`` block whose ``input`` validates against ``_CatalogChangeClassification``).
    """
    tool_use_block = SimpleNamespace(
        type="tool_use", input={"is_catalog_change": is_catalog_change}
    )
    return SimpleNamespace(content=[tool_use_block])


@pytest.mark.parametrize(
    "text",
    [
        "add beard trim for 150 rupees",
        "change haircut to 350",
        "remove beard trim",
    ],
)
def test_is_catalog_change_request_true_for_catalog_write_messages(text: str) -> None:
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_response(is_catalog_change=True)

    with patch("app.agent.catalog_intent.anthropic.Anthropic", return_value=mock_client):
        assert is_catalog_change_request(text) is True


def test_is_catalog_change_request_false_for_availability_message() -> None:
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_response(is_catalog_change=False)

    with patch("app.agent.catalog_intent.anthropic.Anthropic", return_value=mock_client):
        assert is_catalog_change_request("block out Friday morning") is False
