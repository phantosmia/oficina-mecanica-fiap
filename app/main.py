from fastapi import FastAPI

from app.shared.settings import settings
from app.shared.logging_config import RequestIDMiddleware, configure_logging
from app.auth.controller import router as auth_router
from app.clients.controller import router as clients_router
from app.parts.controller import router as parts_router
from app.service_catalog.controller import router as services_router
from app.service_orders.controller import router as service_orders_router
from app.system.controller import router as system_router
from app.vehicles.controller import router as vehicles_router

configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    description="MVP do sistema integrado de atendimento e execução de serviços da oficina mecânica.",
    version="1.0.0",
)

app.add_middleware(RequestIDMiddleware)

app.include_router(auth_router)
app.include_router(system_router)
app.include_router(clients_router)
app.include_router(vehicles_router)
app.include_router(services_router)
app.include_router(parts_router)
app.include_router(service_orders_router)

