from fastapi import APIRouter

from app.slices.system.mapper import to_database_status, to_health_status, to_root_message
from app.slices.system.repository import get_database_status
from app.slices.system.schemas import DatabaseStatus, HealthStatus, RootMessage


router = APIRouter(tags=["system"])


@router.get("/", response_model=RootMessage)
def read_root() -> RootMessage:
    return to_root_message("Oficina Mecânica FIAP API pronta para gestão de ordens de serviço")


@router.get("/health", response_model=HealthStatus)
def healthcheck() -> HealthStatus:
    return to_health_status("ok")


@router.get("/db-status", response_model=DatabaseStatus)
def database_status() -> DatabaseStatus:
    return to_database_status(get_database_status())