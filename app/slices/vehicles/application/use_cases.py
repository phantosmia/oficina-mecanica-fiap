from app.shared.exceptions import NotFoundError
from app.slices.vehicles.domain.entity import VehicleEntity
from app.slices.vehicles.domain.repository import IVehicleRepository


class ListVehiclesUseCase:
    def __init__(self, repo: IVehicleRepository) -> None:
        self._repo = repo

    def execute(self) -> list[VehicleEntity]:
        return self._repo.list()


class GetVehicleUseCase:
    def __init__(self, repo: IVehicleRepository) -> None:
        self._repo = repo

    def execute(self, vehicle_id: int) -> VehicleEntity:
        vehicle = self._repo.get_by_id(vehicle_id)
        if vehicle is None:
            raise NotFoundError("Veículo", vehicle_id)
        return vehicle


class CreateVehicleUseCase:
    def __init__(self, repo: IVehicleRepository) -> None:
        self._repo = repo

    def execute(self, client_id: int, brand: str, model: str, year: int, license_plate: str) -> VehicleEntity:
        return self._repo.create(client_id, brand, model, year, license_plate)


class UpdateVehicleUseCase:
    def __init__(self, repo: IVehicleRepository) -> None:
        self._repo = repo

    def execute(self, vehicle_id: int, fields: dict[str, object]) -> VehicleEntity:
        vehicle = self._repo.update(vehicle_id, fields)
        if vehicle is None:
            raise NotFoundError("Veículo", vehicle_id)
        return vehicle


class DeleteVehicleUseCase:
    def __init__(self, repo: IVehicleRepository) -> None:
        self._repo = repo

    def execute(self, vehicle_id: int) -> None:
        if not self._repo.delete(vehicle_id):
            raise NotFoundError("Veículo", vehicle_id)
