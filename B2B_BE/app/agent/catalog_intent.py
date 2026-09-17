import anthropic
from pydantic import BaseModel, Field

from app.config import settings

_TOOL_NAME = "classify_catalog_change_request"


class _CatalogChangeClassification(BaseModel):
    """The LLM's classification of whether a free-text message is a catalog-change request
    (FR-28's trigger condition).
    """

    is_catalog_change: bool = Field(
        description=(
            "True if the message asks to add a new Service or price, edit/change an existing "
            "Service's details or price, or delete/remove a Service or price — any catalog-write "
            "request. False for browsing/asking questions about existing prices or services "
            "(e.g. 'how much is a haircut?', 'what services do you offer?'), and false for "
            "availability/schedule requests (e.g. blocking or unblocking a staff member's time), "
            "which are a separate concern and must not be misclassified as catalog changes."
        )
    )


def _build_tool_schema() -> dict:
    return {
        "name": _TOOL_NAME,
        "description": "Record whether the message is a catalog add/edit/delete request.",
        "input_schema": _CatalogChangeClassification.model_json_schema(),
    }


def is_catalog_change_request(text: str) -> bool:
    """Classify whether ``text`` is a request to add, edit, or delete a Service or its price
    (FR-28).

    This is the trigger condition a future Manager Agent hook (``handle_staff_catalog_boundary``)
    uses to redirect a Staff-identified speaker away from an Owner/Admin-only action. It has no
    channel-specific branch and no identity awareness of its own — classification is purely over
    the message text, mirroring ``app.agent.booking_intent.parse_booking_intent`` and
    ``app.agent.availability_intent.parse_availability_change``'s shared pattern of a single
    forced Anthropic tool call.

    Deliberately does not fire on availability/schedule requests (e.g. "block out Friday
    morning", FR-25) or on browsing questions about existing prices/services — only on a request
    to change the catalog itself.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=64,
        system=(
            "You classify whether a message is a request to add, edit/change, or delete/remove "
            "a salon Service or its price — a catalog-write request. Positive examples: 'add "
            "beard trim for 150 rupees', 'change haircut to 350', 'remove beard trim'. Negative "
            "examples: questions about existing prices or services (browsing, not changing, "
            "e.g. 'how much is a haircut?'), and availability/schedule requests (e.g. 'block "
            "out Friday morning'), which are a different concern entirely and must not be "
            "classified as a catalog change."
        ),
        messages=[{"role": "user", "content": text}],
        tools=[_build_tool_schema()],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
    )

    tool_use = next(block for block in response.content if block.type == "tool_use")
    classification = _CatalogChangeClassification.model_validate(tool_use.input)

    return classification.is_catalog_change
