from fastapi import HTTPException, status

from app.shared.models import Vehicle
from app.slices.vehicles import repository


def list_vehicles() -> list[Vehicle]:
    return repository.list_vehicles()


def get_vehicle_by_id(vehicle_id: int) -> Vehicle:
    vehicle = repository.get_vehicle_by_id(vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado.")
    return vehicle


def create_vehicle(payload: dict[str, object]) -> Vehicle:
    return repository.create_vehicle(payload)


def update_vehicle(vehicle_id: int, payload: dict[str, object]) -> Vehicle:
    vehicle = repository.update_vehicle(vehicle_id, payload)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado.")
    return vehicle


def delete_vehicle(vehicle_id: int) -> None:
    if not repository.delete_vehicle(vehicle_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado.")
