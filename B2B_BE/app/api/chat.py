"""``POST /chat`` — the Web Chat channel adapter (APPOINTMEN-14).

Per `base-rules.md`'s "channel logic stays a thin adapter" rule: this module
does nothing but translate an HTTP request into a call to
``app.agent.booking_agent.handle_message`` and translate the returned reply
back into an HTTP response. All identity-resolution logic (FR-1) lives in
``booking_agent`` — nothing here forks or duplicates it.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent import booking_agent
from app.db import get_db

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str | None = None


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    reply = booking_agent.handle_message(db, request.session_id, request.message)
    return ChatResponse(reply=reply)
