from datetime import UTC, datetime

from app.agent.prompts.booking_agent import build_booking_agent_system_prompt

KNOWN_SERVICES = ["Haircut", "Beard Trim"]
KNOWN_STAFF = ["Asha", "Ravi"]
CUSTOMER_NAME = "Arjun"
CUSTOMER_ID = 42


def _build(now: datetime, known_staff: list[str] = KNOWN_STAFF) -> str:
    return build_booking_agent_system_prompt(
        now, KNOWN_SERVICES, known_staff, CUSTOMER_NAME, CUSTOMER_ID
    )


def test_build_booking_agent_system_prompt_contains_current_datetime() -> None:
    now = datetime(2026, 9, 18, 14, 30, tzinfo=UTC)

    prompt = _build(now)

    assert now.isoformat() in prompt


def test_build_booking_agent_system_prompt_does_not_raise_for_representative_now() -> None:
    now = datetime(2027, 1, 1, 0, 0, tzinfo=UTC)

    prompt = _build(now)

    assert isinstance(prompt, str)
    assert prompt != ""


def test_build_booking_agent_system_prompt_lists_known_services() -> None:
    now = datetime(2026, 9, 18, 14, 30, tzinfo=UTC)

    prompt = _build(now)

    assert "Haircut" in prompt
    assert "Beard Trim" in prompt


def test_build_booking_agent_system_prompt_lists_known_staff() -> None:
    now = datetime(2026, 9, 18, 14, 30, tzinfo=UTC)

    prompt = _build(now)

    assert "Asha" in prompt
    assert "Ravi" in prompt


def test_build_booking_agent_system_prompt_omits_staff_section_when_none_known() -> None:
    now = datetime(2026, 9, 18, 14, 30, tzinfo=UTC)

    prompt = _build(now, known_staff=[])

    assert "bookable staff are" not in prompt


def test_build_booking_agent_system_prompt_includes_customer_identity() -> None:
    now = datetime(2026, 9, 18, 14, 30, tzinfo=UTC)

    prompt = _build(now)

    assert CUSTOMER_NAME in prompt
    assert str(CUSTOMER_ID) in prompt


def test_build_booking_agent_system_prompt_does_not_promise_unbuilt_capabilities() -> None:
    """Only capabilities BOOKING_TOOLS actually supports should be promised."""
    now = datetime(2026, 9, 18, 14, 30, tzinfo=UTC)

    prompt = _build(now).lower()

    assert "reschedule" not in prompt
    assert "cancel" not in prompt
