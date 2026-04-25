from sqlalchemy import select

from app.shared.database import get_session
from app.shared.models import CatalogService


def list_services() -> list[CatalogService]:
    with get_session() as session:
        return list(session.scalars(select(CatalogService).order_by(CatalogService.id)).all())


def get_service_by_id(service_id: int) -> CatalogService | None:
    with get_session() as session:
        return session.get(CatalogService, service_id)


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


def update_service(service_id: int, payload: dict[str, object]) -> CatalogService | None:
    with get_session() as session:
        service = session.get(CatalogService, service_id)
        if service is None:
            return None

        for key, value in payload.items():
            setattr(service, key, value)
        session.commit()
        session.refresh(service)
        return service


def delete_service(service_id: int) -> bool:
    with get_session() as session:
        service = session.get(CatalogService, service_id)
        if service is None:
            return False

        session.delete(service)
        session.commit()
        return True
