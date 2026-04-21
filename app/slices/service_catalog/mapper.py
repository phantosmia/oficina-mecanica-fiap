from app.shared.models import CatalogService
from app.slices.service_catalog.schemas import CatalogServiceRead


def to_read_model(service: CatalogService) -> CatalogServiceRead:
    return CatalogServiceRead.model_validate(service)
