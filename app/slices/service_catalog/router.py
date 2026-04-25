from fastapi import APIRouter, Depends, Response, status

from app.shared.dependencies import get_current_admin
from app.slices.service_catalog.mapper import to_read_model
from app.slices.service_catalog.schemas import CatalogServiceCreate, CatalogServiceRead, CatalogServiceUpdate
from app.slices.service_catalog import service


router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[CatalogServiceRead], dependencies=[Depends(get_current_admin)])
def get_services() -> list[CatalogServiceRead]:
    return [to_read_model(item) for item in service.list_services()]


@router.get("/{service_id}", response_model=CatalogServiceRead, dependencies=[Depends(get_current_admin)])
def get_service(service_id: int) -> CatalogServiceRead:
    return to_read_model(service.get_service_by_id(service_id))


@router.post("", response_model=CatalogServiceRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
def post_service(payload: CatalogServiceCreate) -> CatalogServiceRead:
    return to_read_model(service.create_service(payload.model_dump()))


@router.put("/{service_id}", response_model=CatalogServiceRead, dependencies=[Depends(get_current_admin)])
def put_service(service_id: int, payload: CatalogServiceUpdate) -> CatalogServiceRead:
    return to_read_model(service.update_service(service_id, payload.model_dump(exclude_none=True)))


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def remove_service(service_id: int) -> Response:
    service.delete_service(service_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
