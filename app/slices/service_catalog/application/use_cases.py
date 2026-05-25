from app.shared.exceptions import NotFoundError
from app.slices.service_catalog.domain.entity import CatalogServiceEntity
from app.slices.service_catalog.domain.repository import ICatalogServiceRepository


class ListCatalogServicesUseCase:
    def __init__(self, repo: ICatalogServiceRepository) -> None:
        self._repo = repo

    def execute(self) -> list[CatalogServiceEntity]:
        return self._repo.list()


class GetCatalogServiceUseCase:
    def __init__(self, repo: ICatalogServiceRepository) -> None:
        self._repo = repo

    def execute(self, service_id: int) -> CatalogServiceEntity:
        service = self._repo.get_by_id(service_id)
        if service is None:
            raise NotFoundError("Serviço", service_id)
        return service


class CreateCatalogServiceUseCase:
    def __init__(self, repo: ICatalogServiceRepository) -> None:
        self._repo = repo

    def execute(
        self,
        name: str,
        description: str | None,
        base_price: float,
        estimated_minutes: int,
        active: bool,
    ) -> CatalogServiceEntity:
        return self._repo.create(name, description, base_price, estimated_minutes, active)


class UpdateCatalogServiceUseCase:
    def __init__(self, repo: ICatalogServiceRepository) -> None:
        self._repo = repo

    def execute(self, service_id: int, fields: dict[str, object]) -> CatalogServiceEntity:
        service = self._repo.update(service_id, fields)
        if service is None:
            raise NotFoundError("Serviço", service_id)
        return service


class DeleteCatalogServiceUseCase:
    def __init__(self, repo: ICatalogServiceRepository) -> None:
        self._repo = repo

    def execute(self, service_id: int) -> None:
        if not self._repo.delete(service_id):
            raise NotFoundError("Serviço", service_id)
