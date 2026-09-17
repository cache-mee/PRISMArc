from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.config import settings

app = FastAPI(title=settings.app_name)
app.include_router(chat_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
