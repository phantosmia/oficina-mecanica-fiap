from app.service_catalog.domain.entity import CatalogServiceEntity
from app.service_catalog.schemas import CatalogServiceRead


def to_response(entity: CatalogServiceEntity) -> CatalogServiceRead:
    return CatalogServiceRead(
        id=entity.id,
        name=entity.name,
        description=entity.description,
        base_price=entity.base_price,
        estimated_minutes=entity.estimated_minutes,
        active=entity.active,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
