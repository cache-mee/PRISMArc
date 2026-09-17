from fastapi import FastAPI

from app.api.appointments import router as appointments_router
from app.api.chat import router as chat_router
from app.api.webhooks.whatsapp import router as whatsapp_webhook_router
from app.config import settings

app = FastAPI(title=settings.app_name)
app.include_router(chat_router)
app.include_router(appointments_router)
app.include_router(whatsapp_webhook_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
