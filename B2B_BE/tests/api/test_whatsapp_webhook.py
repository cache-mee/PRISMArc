"""``POST /webhooks/whatsapp`` round-trip coverage (APPOINTMEN-48/49/55).

No test module for this webhook existed prior to APPOINTMEN-55: both
APPOINTMEN-48 and APPOINTMEN-49's own commits recorded "webhook-level tests
intentionally not written this cycle per standing user override." APPOINTMEN-
55 Task 7 extends ``manager_agent.resolve_and_greet_speaker``'s call site here
with ``db``/``Body`` — this module closes that pre-existing gap enough to
prove the extended call signature is actually wired end to end through a real
``TestClient`` request/response round trip, per Task 7's own testing
requirements.

``manager_agent.resolve_and_greet_speaker`` and ``booking_agent.handle_message``
are mocked in every test below — neither touches the database or an LLM
provider directly, so no live Postgres/LLM credentials are required.
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_whatsapp_webhook_passes_body_and_db_to_manager_agent_and_returns_its_reply(
    client: TestClient,
) -> None:
    mock_resolve_and_greet = AsyncMock(return_value="Sure, blocking Friday morning.")
    mock_handle_message = AsyncMock()

    with (
        patch(
            "app.api.webhooks.whatsapp.manager_agent.resolve_and_greet_speaker",
            mock_resolve_and_greet,
        ),
        patch(
            "app.api.webhooks.whatsapp.booking_agent.handle_message",
            mock_handle_message,
        ),
    ):
        response = client.post(
            "/webhooks/whatsapp",
            data={
                "From": "whatsapp:+911234567890",
                "Body": "I'm unavailable Friday morning",
            },
        )

    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "Sure, blocking Friday morning." in response.text

    mock_resolve_and_greet.assert_called_once()
    call_args = mock_resolve_and_greet.call_args.args
    assert call_args[0] == "whatsapp:+911234567890"
    assert call_args[1] == "+911234567890"
    # call_args[2] is the request-scoped `db` (AsyncSession) — not asserted by
    # identity, just proven present (not None) and passed through positionally.
    assert call_args[2] is not None
    assert call_args[3] == "I'm unavailable Friday morning"

    # A Staff/Owner match short-circuits the turn — the customer flow must
    # never run for it.
    mock_handle_message.assert_not_called()


def test_whatsapp_webhook_falls_through_to_booking_agent_on_no_manager_match(
    client: TestClient,
) -> None:
    mock_resolve_and_greet = AsyncMock(return_value=None)
    mock_handle_message = AsyncMock(return_value="Hi! What's your name?")

    with (
        patch(
            "app.api.webhooks.whatsapp.manager_agent.resolve_and_greet_speaker",
            mock_resolve_and_greet,
        ),
        patch(
            "app.api.webhooks.whatsapp.booking_agent.handle_message",
            mock_handle_message,
        ),
    ):
        response = client.post(
            "/webhooks/whatsapp",
            data={
                "From": "whatsapp:+919999999999",
                "Body": "I'd like to book a haircut",
            },
        )

    assert response.status_code == 200
    assert "Hi! What's your name?" in response.text
    mock_handle_message.assert_called_once()
