from fastapi import APIRouter

from app.slices.system.mapper import to_database_status, to_health_status, to_root_message
from app.slices.system.schemas import DatabaseStatus, HealthStatus, RootMessage
from app.slices.system import service


router = APIRouter(tags=["system"])


@router.get("/", response_model=RootMessage)
def read_root() -> RootMessage:
    return to_root_message(service.get_root_message())


@router.get("/health", response_model=HealthStatus)
def healthcheck() -> HealthStatus:
    return to_health_status(service.get_health_status())


@router.get("/db-status", response_model=DatabaseStatus)
def database_status() -> DatabaseStatus:
    return to_database_status(service.get_database_status())