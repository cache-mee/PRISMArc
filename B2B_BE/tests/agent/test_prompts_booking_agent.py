from datetime import UTC, datetime

from app.agent.prompts.booking_agent import build_booking_agent_system_prompt


def test_build_booking_agent_system_prompt_contains_current_datetime() -> None:
    now = datetime(2026, 9, 18, 14, 30, tzinfo=UTC)

    prompt = build_booking_agent_system_prompt(now)

    assert now.isoformat() in prompt


def test_build_booking_agent_system_prompt_does_not_raise_for_representative_now() -> None:
    now = datetime(2027, 1, 1, 0, 0, tzinfo=UTC)

    prompt = build_booking_agent_system_prompt(now)

    assert isinstance(prompt, str)
    assert prompt != ""
