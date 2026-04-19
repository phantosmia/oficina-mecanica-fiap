from fastapi import APIRouter

from app.slices.vehicles.repository import list_vehicles
from app.slices.vehicles.schemas import VehicleRead


router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleRead])
def get_vehicles() -> list[VehicleRead]:
    return [VehicleRead.model_validate(vehicle) for vehicle in list_vehicles()]