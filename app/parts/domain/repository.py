from abc import ABC, abstractmethod

from app.parts.domain.entity import PartEntity


class IPartRepository(ABC):
    @abstractmethod
    def list(self) -> list[PartEntity]: ...

    @abstractmethod
    def get_by_id(self, part_id: int) -> PartEntity | None: ...

    @abstractmethod
    def create(
        self,
        name: str,
        sku: str,
        description: str | None,
        unit_price: float,
        stock_quantity: int,
        min_stock_level: int,
    ) -> PartEntity: ...

    @abstractmethod
    def update(self, part_id: int, fields: dict[str, object]) -> PartEntity | None: ...

    @abstractmethod
    def delete(self, part_id: int) -> bool: ...
