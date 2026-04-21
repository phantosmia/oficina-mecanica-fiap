from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.shared.database import init_database
from app.shared.settings import settings
from app.slices.auth.router import router as auth_router
from app.slices.clients.router import router as clients_router
from app.slices.parts.router import router as parts_router
from app.slices.service_catalog.router import router as services_router
from app.slices.service_orders.router import router as service_orders_router
from app.slices.system.router import router as system_router
from app.slices.vehicles.router import router as vehicles_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    description="MVP do sistema integrado de atendimento e execução de serviços da oficina mecânica.",
    version="1.0.0",
)


app.include_router(auth_router)
app.include_router(system_router)
app.include_router(clients_router)
app.include_router(vehicles_router)
app.include_router(services_router)
app.include_router(parts_router)
app.include_router(service_orders_router)

