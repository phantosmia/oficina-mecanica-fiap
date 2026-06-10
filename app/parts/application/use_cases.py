from app.shared.exceptions import ConflictError, NotFoundError
from app.parts.domain.entity import PartEntity
from app.parts.domain.repository import IPartRepository


class ListPartsUseCase:
    def __init__(self, repo: IPartRepository) -> None:
        self._repo = repo

    def execute(self) -> list[PartEntity]:
        return self._repo.list()


class GetPartUseCase:
    def __init__(self, repo: IPartRepository) -> None:
        self._repo = repo

    def execute(self, part_id: int) -> PartEntity:
        part = self._repo.get_by_id(part_id)
        if part is None:
            raise NotFoundError("Peça/insumo", part_id)
        return part


class CreatePartUseCase:
    def __init__(self, repo: IPartRepository) -> None:
        self._repo = repo

    def execute(
        self,
        name: str,
        sku: str,
        description: str | None,
        unit_price: float,
        stock_quantity: int,
        min_stock_level: int,
    ) -> PartEntity:
        try:
            return self._repo.create(name, sku, description, unit_price, stock_quantity, min_stock_level)
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc


class UpdatePartUseCase:
    def __init__(self, repo: IPartRepository) -> None:
        self._repo = repo

    def execute(self, part_id: int, fields: dict[str, object]) -> PartEntity:
        try:
            part = self._repo.update(part_id, fields)
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc
        if part is None:
            raise NotFoundError("Peça/insumo", part_id)
        return part


class DeletePartUseCase:
    def __init__(self, repo: IPartRepository) -> None:
        self._repo = repo

    def execute(self, part_id: int) -> None:
        if not self._repo.delete(part_id):
            raise NotFoundError("Peça/insumo", part_id)
