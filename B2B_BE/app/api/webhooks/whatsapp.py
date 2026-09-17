"""``POST /webhooks/whatsapp`` — the WhatsApp channel adapter (APPOINTMEN-48).

Per `base-rules.md`'s "channel logic stays a thin adapter" rule: this module
does nothing but translate Twilio's inbound webhook form payload into a call
to ``app.agent.booking_agent.handle_message`` and translate the returned
reply back into a TwiML XML response. All identity-resolution logic (FR-1/
FR-3) lives in ``booking_agent`` — nothing here forks or duplicates it.

No Twilio webhook signature verification (``X-Twilio-Signature``) is done
here — explicitly out of scope for this ticket (see the APPOINTMEN-48
implementation plan's Security Considerations / Out of Scope). No outbound
Twilio REST calls are made and no Account SID/Auth Token/From-number config
is needed: Twilio expects the reply as TwiML in the synchronous HTTP response
body, which ``twilio.twiml.messaging_response.MessagingResponse`` renders
without any credentials.

**Session keying:** WhatsApp has no client-supplied, browser-style
``session_id`` the way Web Chat does. The sender's phone number is the only
stable per-conversation identifier the webhook gets, so the adapter derives
``session_id = f"whatsapp:{phone_number}"`` deterministically from it and
uses that as the (unchanged) ``session_store`` key.
"""

from fastapi import APIRouter, Depends, Form
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.twiml.messaging_response import MessagingResponse

from app.agent import booking_agent
from app.database import get_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_WHATSAPP_PREFIX = "whatsapp:"


def _strip_whatsapp_prefix(raw_from: str) -> str:
    """Strip Twilio's ``whatsapp:`` URI prefix from an inbound ``From`` value.

    Returns the plain phone number in the exact string format
    ``Customer.phone_number`` is stored/looked up in — no further
    normalization, consistent with the existing exact-match repository
    lookup (``app.repositories.customers.get_customer_by_phone``).
    """
    if raw_from.startswith(_WHATSAPP_PREFIX):
        return raw_from[len(_WHATSAPP_PREFIX) :]
    return raw_from


@router.post("/whatsapp")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Handle one inbound Twilio WhatsApp webhook call.

    Strips the ``whatsapp:`` prefix from ``From`` to get the sender's raw
    phone number, derives a deterministic ``session_id`` from it, and calls
    the shared ``booking_agent.handle_message`` with that phone number
    supplied out-of-band — so identity resolution never asks a WhatsApp
    customer for their number (FR-3). The reply is rendered as TwiML.
    """
    phone_number = _strip_whatsapp_prefix(From)
    session_id = f"whatsapp:{phone_number}"

    reply = await booking_agent.handle_message(
        db, session_id, Body, phone_number=phone_number
    )

    twiml = MessagingResponse()
    twiml.message(reply)
    return Response(content=str(twiml), media_type="application/xml")
