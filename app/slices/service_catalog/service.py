from fastapi import HTTPException, status

from app.shared.models import CatalogService
from app.slices.service_catalog import repository


def list_services() -> list[CatalogService]:
    return repository.list_services()


def get_service_by_id(service_id: int) -> CatalogService:
    service = repository.get_service_by_id(service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado.")
    return service


def create_service(payload: dict[str, object]) -> CatalogService:
    return repository.create_service(payload)


def update_service(service_id: int, payload: dict[str, object]) -> CatalogService:
    service = repository.update_service(service_id, payload)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado.")
    return service


def delete_service(service_id: int) -> None:
    if not repository.delete_service(service_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado.")
