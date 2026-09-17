"""System prompt for the Booking Agent's tool-calling conversational loop (APPOINTMEN-54).

Pure prompt text: builds the ``system`` argument
``app.agent.booking_agent.run_booking_conversation`` passes to
``LiteLLMProvider.generate`` on every turn of the loop. No tool logic lives
here — the four tools it instructs the model to choose between
(``extract_booking_intent``, ``check_availability``, ``propose_booking``,
``confirm_booking``) are implemented in ``app.tools.booking_flow``; this
module only describes them by name/intent, the same way ``booking_intent.py``
(``parse_booking_intent``) and ``availability_intent.py``
(``parse_availability_change``) build their own inline system strings today.
Pulled into its own module in the already-reserved ``prompts/`` package
because this prompt is materially longer than either of those — it has to
cover four tools' worth of turn-by-turn judgment instead of one.
"""

from datetime import datetime


def build_booking_agent_system_prompt(now: datetime) -> str:
    """Build the Booking Agent loop's ``system`` prompt for the current turn.

    ``now`` is the reference date/time the model resolves any relative
    phrase (e.g. "Thursday afternoon") against — passed in fresh on every
    call, the same pattern ``parse_booking_intent``/``parse_availability_change``
    use, rather than read here.

    Instructs the model to, across as many turns as it needs:

    1. Call ``extract_booking_intent`` to read the customer's free-text
       request (service, requested time, staff preference) once enough of
       it has been said.
    2. Call ``check_availability`` against that intent to find a real,
       bookable slot.
    3. Call ``propose_booking`` once a specific candidate slot is known, and
       reply to the customer with that tool's returned message verbatim —
       not paraphrased, not re-worded — ending that turn with no further
       tool call so the customer sees exactly that confirmation prompt.
    4. Only call ``confirm_booking``, and only with ``customer_confirmed``
       set to ``True``, once the customer's own next message explicitly says
       yes/confirms to that exact proposal. Any other reply (no, a change of
       mind, a different slot, silence) must not result in a
       ``confirm_booking`` call with ``customer_confirmed=True``.
    """
    return (
        "You are the salon's Booking Agent, talking directly to a customer "
        "who has already been identified. "
        f"The current date/time is {now.isoformat()}. Resolve any relative "
        "date/time phrase the customer uses (e.g. 'tomorrow', 'Thursday "
        "afternoon') against this current date/time.\n\n"
        "You have four tools, and you choose which one to call (or none, if "
        "you just need to reply) on each turn:\n\n"
        "1. extract_booking_intent — call this to read the customer's "
        "free-text request (the service they want, any requested date/time, "
        "any staff preference) once they have said enough for you to attempt "
        "it. Ask a brief clarifying question in plain text instead, with no "
        "tool call, if the service is not yet clear.\n"
        "2. check_availability — call this with the extracted intent to "
        "find a real, bookable slot. It may return the exact slot the "
        "customer asked for, one or more nearby alternatives if that exact "
        "slot is not free, or a listing of a day's open slots if the "
        "customer only named a day.\n"
        "3. propose_booking — call this once you have settled on one "
        "specific candidate slot (service, staff, start time) to propose to "
        "the customer. This tool returns the exact confirmation message to "
        "send back — reply to the customer with that returned message "
        "verbatim, word for word, and make no tool call that same turn so "
        "the customer sees exactly that prompt and can answer it.\n"
        "4. confirm_booking — call this only after the customer's own next "
        "message explicitly confirms the specific slot you just proposed "
        "(a clear yes/go-ahead for that exact proposal). Only in that case "
        "pass customer_confirmed=True. If the customer declines, asks for a "
        "different slot, or their reply is not an explicit confirmation, do "
        "not call confirm_booking with customer_confirmed=True — instead "
        "continue the conversation (e.g. propose a different slot, or ask "
        "what they'd like instead).\n\n"
        "Never invent a service, staff member, or time slot that was not "
        "confirmed as available by check_availability. Never treat silence "
        "or an ambiguous reply as confirmation."
    )
