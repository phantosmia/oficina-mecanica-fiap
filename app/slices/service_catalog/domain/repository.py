from abc import ABC, abstractmethod

from app.slices.service_catalog.domain.entity import CatalogServiceEntity


class ICatalogServiceRepository(ABC):
    @abstractmethod
    def list(self) -> list[CatalogServiceEntity]: ...

    @abstractmethod
    def get_by_id(self, service_id: int) -> CatalogServiceEntity | None: ...

    @abstractmethod
    def create(
        self,
        name: str,
        description: str | None,
        base_price: float,
        estimated_minutes: int,
        active: bool,
    ) -> CatalogServiceEntity: ...

    @abstractmethod
    def update(self, service_id: int, fields: dict[str, object]) -> CatalogServiceEntity | None: ...

    @abstractmethod
    def delete(self, service_id: int) -> bool: ...
