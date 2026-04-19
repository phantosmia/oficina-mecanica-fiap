from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.shared.database import init_database
from app.slices.clients.router import router as clients_router
from app.slices.system.router import router as system_router
from app.slices.vehicles.router import router as vehicles_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="Oficina Mecânica FIAP", lifespan=lifespan)


app.include_router(system_router)
app.include_router(clients_router)
app.include_router(vehicles_router)

