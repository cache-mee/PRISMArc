import logging

from fastapi import FastAPI

from app.api.appointments import router as appointments_router
from app.api.chat import router as chat_router
from app.api.dashboard import router as dashboard_router
from app.api.webhooks.whatsapp import router as whatsapp_webhook_router
from app.config import settings

# ``app.agent.*``/``app.api.*`` already call ``logging.getLogger(__name__).info``/
# ``.exception`` throughout, but nothing previously attached a handler to the root
# logger, so only the ``WARNING``+ output Python's no-handler "last resort" fallback
# prints made it to the console — every ``.info`` call (agent turn start/end) and full
# exception tracebacks logged elsewhere were silently dropped.
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title=settings.app_name)
app.include_router(chat_router)
app.include_router(appointments_router)
app.include_router(dashboard_router)
app.include_router(whatsapp_webhook_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
