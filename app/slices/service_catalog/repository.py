from fastapi import HTTPException, status
from sqlalchemy import select

from app.shared.database import get_session
from app.shared.models import CatalogService


def list_services() -> list[CatalogService]:
    with get_session() as session:
        return list(session.scalars(select(CatalogService).order_by(CatalogService.id)).all())


def get_service_by_id(service_id: int) -> CatalogService:
    with get_session() as session:
        service = session.get(CatalogService, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado.")
    return service


def create_service(payload: dict[str, object]) -> CatalogService:
    with get_session() as session:
        service = CatalogService(
            name=str(payload["name"]),
            description=payload.get("description"),
            base_price=float(payload["base_price"]),
            estimated_minutes=int(payload["estimated_minutes"]),
            active=bool(payload.get("active", True)),
        )
        session.add(service)
        session.commit()
        session.refresh(service)
        return service


def update_service(service_id: int, payload: dict[str, object]) -> CatalogService:
    with get_session() as session:
        service = session.get(CatalogService, service_id)
        if service is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado.")

        for key, value in payload.items():
            setattr(service, key, value)
        session.commit()
        session.refresh(service)
        return service


def delete_service(service_id: int) -> None:
    with get_session() as session:
        service = session.get(CatalogService, service_id)
        if service is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado.")

        session.delete(service)
        session.commit()
