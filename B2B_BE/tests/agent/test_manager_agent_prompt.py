from app.agent.manager_agent import SpeakerContext
from app.agent.prompts.manager_agent_prompt import render_manager_agent_system_prompt
from app.models.staff import StaffRole

STAFF_SPEAKER = SpeakerContext(id=1, name="Dr. Rao", role=StaffRole.STAFF)
OWNER_ADMIN_SPEAKER = SpeakerContext(id=2, name="Ramesh", role=StaffRole.OWNER_ADMIN)


def test_prompt_includes_speaker_name_for_staff() -> None:
    prompt = render_manager_agent_system_prompt(STAFF_SPEAKER)

    assert "Dr. Rao" in prompt


def test_prompt_includes_speaker_name_for_owner_admin() -> None:
    prompt = render_manager_agent_system_prompt(OWNER_ADMIN_SPEAKER)

    assert "Ramesh" in prompt


def test_prompt_names_resolved_role_for_staff() -> None:
    prompt = render_manager_agent_system_prompt(STAFF_SPEAKER)

    assert "Staff" in prompt


def test_prompt_names_resolved_role_for_owner_admin() -> None:
    prompt = render_manager_agent_system_prompt(OWNER_ADMIN_SPEAKER)

    assert "Owner/Admin" in prompt


def test_prompt_wording_is_distinct_between_roles() -> None:
    staff_prompt = render_manager_agent_system_prompt(STAFF_SPEAKER)
    owner_admin_prompt = render_manager_agent_system_prompt(
        OWNER_ADMIN_SPEAKER.model_copy(update={"name": STAFF_SPEAKER.name})
    )

    assert staff_prompt != owner_admin_prompt


def test_staff_prompt_mentions_availability_change_capability() -> None:
    prompt = render_manager_agent_system_prompt(STAFF_SPEAKER)

    assert "availability" in prompt.lower()


def test_owner_admin_prompt_states_they_do_not_manage_own_availability() -> None:
    prompt = render_manager_agent_system_prompt(OWNER_ADMIN_SPEAKER)

    assert "own availability" in prompt.lower()


def test_prompt_instructs_calling_tools_rather_than_answering_from_memory() -> None:
    prompt = render_manager_agent_system_prompt(STAFF_SPEAKER)

    assert "call" in prompt.lower()
    assert "tool" in prompt.lower()
    assert "from memory" in prompt.lower()


def test_prompt_does_not_leak_other_speakers_identity() -> None:
    staff_prompt = render_manager_agent_system_prompt(STAFF_SPEAKER)
    owner_admin_prompt = render_manager_agent_system_prompt(OWNER_ADMIN_SPEAKER)

    assert OWNER_ADMIN_SPEAKER.name not in staff_prompt
    assert STAFF_SPEAKER.name not in owner_admin_prompt


def test_prompt_does_not_name_any_specific_tool() -> None:
    """The tool list itself is passed via ``tools=`` — the prompt stays behavioral."""
    prompt = render_manager_agent_system_prompt(STAFF_SPEAKER)

    for tool_name in (
        "verify_booking_intent",
        "verify_alternative_slot",
        "verify_conflict_check",
        "propose_availability_change",
        "confirm_availability_change",
    ):
        assert tool_name not in prompt
