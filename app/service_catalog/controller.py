from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.dependencies import get_current_admin
from app.shared.http_errors import domain_error_handler
from app.service_catalog.adapters.presenter import to_response
from app.service_catalog.adapters.sqlalchemy_repository import SqlAlchemyCatalogServiceRepository
from app.service_catalog.application.use_cases import (
    CreateCatalogServiceUseCase,
    DeleteCatalogServiceUseCase,
    GetCatalogServiceUseCase,
    ListCatalogServicesUseCase,
    UpdateCatalogServiceUseCase,
)
from app.service_catalog.domain.repository import ICatalogServiceRepository
from app.service_catalog.schemas import CatalogServiceCreate, CatalogServiceRead, CatalogServiceUpdate

router = APIRouter(prefix="/services", tags=["services"])


def _get_repo(session: Session = Depends(get_db)) -> ICatalogServiceRepository:
    return SqlAlchemyCatalogServiceRepository(session)


@router.get("", response_model=list[CatalogServiceRead], dependencies=[Depends(get_current_admin)])
def get_services(repo: ICatalogServiceRepository = Depends(_get_repo)) -> list[CatalogServiceRead]:
    return [to_response(s) for s in ListCatalogServicesUseCase(repo).execute()]


@router.get("/{service_id}", response_model=CatalogServiceRead, dependencies=[Depends(get_current_admin)])
def get_service(service_id: int, repo: ICatalogServiceRepository = Depends(_get_repo)) -> CatalogServiceRead:
    with domain_error_handler():
        return to_response(GetCatalogServiceUseCase(repo).execute(service_id))


@router.post("", response_model=CatalogServiceRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
def post_service(payload: CatalogServiceCreate, repo: ICatalogServiceRepository = Depends(_get_repo)) -> CatalogServiceRead:
    return to_response(
        CreateCatalogServiceUseCase(repo).execute(
            name=payload.name,
            description=payload.description,
            base_price=payload.base_price,
            estimated_minutes=payload.estimated_minutes,
            active=payload.active,
        )
    )


@router.put("/{service_id}", response_model=CatalogServiceRead, dependencies=[Depends(get_current_admin)])
def put_service(service_id: int, payload: CatalogServiceUpdate, repo: ICatalogServiceRepository = Depends(_get_repo)) -> CatalogServiceRead:
    with domain_error_handler():
        return to_response(UpdateCatalogServiceUseCase(repo).execute(service_id, payload.model_dump(exclude_none=True)))


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def remove_service(service_id: int, repo: ICatalogServiceRepository = Depends(_get_repo)) -> Response:
    with domain_error_handler():
        DeleteCatalogServiceUseCase(repo).execute(service_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
