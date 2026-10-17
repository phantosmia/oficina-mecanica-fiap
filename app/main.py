from fastapi import FastAPI

from app.shared.settings import settings
from app.shared.logging_config import RequestIDMiddleware, configure_logging
from app.auth.controller import router as auth_router
from app.clients.controller import router as clients_router
from app.service_orders.controller import router as service_orders_router
from app.system.controller import router as system_router
from app.vehicles.controller import router as vehicles_router

configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    description=(
        "OS Service da oficina mecânica: clientes, veículos, ordens de serviço e orquestrador da saga que coordena "
        "Catálogo, Estoque, Execução, Orçamento e Pagamento (Fase 4). Emite o JWT de admin usado pelos demais serviços."
    ),
    version="1.0.0",
)

app.add_middleware(RequestIDMiddleware)

app.include_router(auth_router)
app.include_router(system_router)
app.include_router(clients_router)
app.include_router(vehicles_router)
app.include_router(service_orders_router)

