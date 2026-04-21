from datetime import UTC, datetime

from sqlalchemy import select

from app.shared.database import get_session
from app.shared.models import Vehicle


def list_vehicles() -> list[Vehicle]:
    with get_session() as session:
        return list(session.scalars(select(Vehicle).order_by(Vehicle.id)).all())


def get_vehicle_by_id(vehicle_id: int) -> Vehicle | None:
    with get_session() as session:
        return session.get(Vehicle, vehicle_id)


def create_vehicle(payload: dict[str, object]) -> Vehicle:
    with get_session() as session:
        vehicle = Vehicle(
            client_id=int(payload["client_id"]),
            brand=str(payload["brand"]),
            model=str(payload["model"]),
            year=int(payload["year"]),
            license_plate=str(payload["license_plate"]),
        )
        session.add(vehicle)
        session.commit()
        session.refresh(vehicle)
        return vehicle


def update_vehicle(vehicle_id: int, payload: dict[str, object]) -> Vehicle | None:
    with get_session() as session:
        vehicle = session.get(Vehicle, vehicle_id)
        if vehicle is None:
            return None

        for key, value in payload.items():
            setattr(vehicle, key, value)
        vehicle.updated_at = datetime.now(UTC)
        session.commit()
        session.refresh(vehicle)
        return vehicle


def delete_vehicle(vehicle_id: int) -> bool:
    with get_session() as session:
        vehicle = session.get(Vehicle, vehicle_id)
        if vehicle is None:
            return False

        session.delete(vehicle)
        session.commit()
        return True