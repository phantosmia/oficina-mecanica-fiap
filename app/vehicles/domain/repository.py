from abc import ABC, abstractmethod

from app.vehicles.domain.entity import VehicleEntity


class IVehicleRepository(ABC):
    @abstractmethod
    def list(self) -> list[VehicleEntity]: ...

    @abstractmethod
    def get_by_id(self, vehicle_id: int) -> VehicleEntity | None: ...

    @abstractmethod
    def create(
        self,
        client_id: int,
        brand: str,
        model: str,
        year: int,
        license_plate: str,
    ) -> VehicleEntity: ...

    @abstractmethod
    def update(self, vehicle_id: int, fields: dict[str, object]) -> VehicleEntity | None: ...

    @abstractmethod
    def delete(self, vehicle_id: int) -> bool: ...
