"""``POST /chat`` — the Web Chat channel adapter (APPOINTMEN-14).

Per `base-rules.md`'s "channel logic stays a thin adapter" rule: this module
does nothing but translate an HTTP request into a call to
``app.agent.booking_agent.handle_message`` and translate the returned reply
back into an HTTP response. All identity-resolution logic (FR-1) lives in
``booking_agent`` — nothing here forks or duplicates it.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import booking_agent
from app.database import get_db

router = APIRouter()

_logger = logging.getLogger(__name__)

CHAT_ERROR_MESSAGE = "Failed to process your request. Please try again later."


class ChatRequest(BaseModel):
    session_id: str
    message: str | None = None


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    try:
        reply = await booking_agent.handle_message(
            db, request.session_id, request.message
        )
    except Exception:
        _logger.exception(
            "Unhandled error while processing chat message for session %s",
            request.session_id,
        )
        raise HTTPException(status_code=500, detail=CHAT_ERROR_MESSAGE) from None
    return ChatResponse(reply=reply)
