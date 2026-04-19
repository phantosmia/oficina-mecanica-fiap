from fastapi import APIRouter

from app.slices.system.repository import get_database_status
from app.slices.system.schemas import DatabaseStatus, HealthStatus, RootMessage


router = APIRouter(tags=["system"])


@router.get("/", response_model=RootMessage)
def read_root() -> RootMessage:
    return RootMessage(message="Oficina Mecânica FIAP API")


@router.get("/health", response_model=HealthStatus)
def healthcheck() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/db-status", response_model=DatabaseStatus)
def database_status() -> DatabaseStatus:
    return DatabaseStatus.model_validate(get_database_status())