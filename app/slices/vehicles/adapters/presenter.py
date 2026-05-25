from app.slices.vehicles.domain.entity import VehicleEntity
from app.slices.vehicles.schemas import VehicleRead


def to_response(entity: VehicleEntity) -> VehicleRead:
    return VehicleRead(
        id=entity.id,
        client_id=entity.client_id,
        brand=entity.brand,
        model=entity.model,
        year=entity.year,
        license_plate=entity.license_plate,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
