from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.shared.dependencies import get_current_admin
from app.slices.vehicles.mapper import to_read_model
from app.slices.vehicles.repository import create_vehicle, delete_vehicle, get_vehicle_by_id, list_vehicles, update_vehicle
from app.slices.vehicles.schemas import VehicleCreate, VehicleRead, VehicleUpdate


router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleRead], dependencies=[Depends(get_current_admin)])
def get_vehicles() -> list[VehicleRead]:
    return [to_read_model(vehicle) for vehicle in list_vehicles()]


@router.get("/{vehicle_id}", response_model=VehicleRead, dependencies=[Depends(get_current_admin)])
def get_vehicle(vehicle_id: int) -> VehicleRead:
    vehicle = get_vehicle_by_id(vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado.")
    return to_read_model(vehicle)


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
def post_vehicle(payload: VehicleCreate) -> VehicleRead:
    return to_read_model(create_vehicle(payload.model_dump()))


@router.put("/{vehicle_id}", response_model=VehicleRead, dependencies=[Depends(get_current_admin)])
def put_vehicle(vehicle_id: int, payload: VehicleUpdate) -> VehicleRead:
    vehicle = update_vehicle(vehicle_id, payload.model_dump(exclude_none=True))
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado.")
    return to_read_model(vehicle)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def remove_vehicle(vehicle_id: int) -> Response:
    if not delete_vehicle(vehicle_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)