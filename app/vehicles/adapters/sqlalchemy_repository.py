from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.models import Vehicle as VehicleORM
from app.vehicles.domain.entity import VehicleEntity
from app.vehicles.domain.repository import IVehicleRepository


def _to_entity(orm: VehicleORM) -> VehicleEntity:
    return VehicleEntity(
        id=orm.id,
        client_id=orm.client_id,
        brand=orm.brand,
        model=orm.model,
        year=orm.year,
        license_plate=orm.license_plate,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SqlAlchemyVehicleRepository(IVehicleRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> list[VehicleEntity]:
        return [_to_entity(v) for v in self._session.scalars(select(VehicleORM).order_by(VehicleORM.id)).all()]

    def get_by_id(self, vehicle_id: int) -> VehicleEntity | None:
        orm = self._session.get(VehicleORM, vehicle_id)
        return _to_entity(orm) if orm else None

    def create(self, client_id: int, brand: str, model: str, year: int, license_plate: str) -> VehicleEntity:
        vehicle = VehicleORM(
            client_id=client_id,
            brand=brand,
            model=model,
            year=year,
            license_plate=license_plate,
        )
        self._session.add(vehicle)
        self._session.commit()
        self._session.refresh(vehicle)
        return _to_entity(vehicle)

    def update(self, vehicle_id: int, fields: dict[str, object]) -> VehicleEntity | None:
        vehicle = self._session.get(VehicleORM, vehicle_id)
        if vehicle is None:
            return None
        for key, value in fields.items():
            setattr(vehicle, key, value)
        vehicle.updated_at = datetime.now(UTC)
        self._session.commit()
        self._session.refresh(vehicle)
        return _to_entity(vehicle)

    def delete(self, vehicle_id: int) -> bool:
        vehicle = self._session.get(VehicleORM, vehicle_id)
        if vehicle is None:
            return False
        self._session.delete(vehicle)
        self._session.commit()
        return True
