from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.models import CatalogService as CatalogServiceORM
from app.slices.service_catalog.domain.entity import CatalogServiceEntity
from app.slices.service_catalog.domain.repository import ICatalogServiceRepository


def _to_entity(orm: CatalogServiceORM) -> CatalogServiceEntity:
    return CatalogServiceEntity(
        id=orm.id,
        name=orm.name,
        description=orm.description,
        base_price=orm.base_price,
        estimated_minutes=orm.estimated_minutes,
        active=orm.active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SqlAlchemyCatalogServiceRepository(ICatalogServiceRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> list[CatalogServiceEntity]:
        return [_to_entity(s) for s in self._session.scalars(select(CatalogServiceORM).order_by(CatalogServiceORM.id)).all()]

    def get_by_id(self, service_id: int) -> CatalogServiceEntity | None:
        orm = self._session.get(CatalogServiceORM, service_id)
        return _to_entity(orm) if orm else None

    def create(
        self,
        name: str,
        description: str | None,
        base_price: float,
        estimated_minutes: int,
        active: bool,
    ) -> CatalogServiceEntity:
        service = CatalogServiceORM(
            name=name,
            description=description,
            base_price=base_price,
            estimated_minutes=estimated_minutes,
            active=active,
        )
        self._session.add(service)
        self._session.commit()
        self._session.refresh(service)
        return _to_entity(service)

    def update(self, service_id: int, fields: dict[str, object]) -> CatalogServiceEntity | None:
        service = self._session.get(CatalogServiceORM, service_id)
        if service is None:
            return None
        for key, value in fields.items():
            setattr(service, key, value)
        self._session.commit()
        self._session.refresh(service)
        return _to_entity(service)

    def delete(self, service_id: int) -> bool:
        service = self._session.get(CatalogServiceORM, service_id)
        if service is None:
            return False
        self._session.delete(service)
        self._session.commit()
        return True
