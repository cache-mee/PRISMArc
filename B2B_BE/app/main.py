from fastapi import FastAPI

from app.api.services import router as services_router

app = FastAPI(title="AppointmentDOTCom Backend")

app.include_router(services_router)
