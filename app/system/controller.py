from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.system.adapters.sqlalchemy_repository import SqlAlchemySystemRepository
from app.system.application.use_cases import GetDatabaseStatusUseCase
from app.system.domain.repository import ISystemRepository
from app.system.schemas import DatabaseStatus, HealthStatus, RootMessage

router = APIRouter(tags=["system"])


def _get_repo(session: Session = Depends(get_db)) -> ISystemRepository:
    return SqlAlchemySystemRepository(session)


@router.get("/", response_model=RootMessage)
def read_root() -> RootMessage:
    return RootMessage(message="Oficina Mecânica FIAP API pronta para gestão de ordens de serviço")


@router.get("/health", response_model=HealthStatus)
def healthcheck() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/db-status", response_model=DatabaseStatus)
def database_status(repo: ISystemRepository = Depends(_get_repo)) -> DatabaseStatus:
    entity = GetDatabaseStatusUseCase(repo).execute()
    return DatabaseStatus(
        database=entity.database,
        path=entity.path,
        clients=entity.clients,
        vehicles=entity.vehicles,
        services=entity.services,
        parts=entity.parts,
        service_orders=entity.service_orders,
    )
