from app.shared.models import Vehicle
from app.slices.vehicles.schemas import VehicleRead


def to_read_model(vehicle: Vehicle) -> VehicleRead:
    return VehicleRead.model_validate(vehicle)
