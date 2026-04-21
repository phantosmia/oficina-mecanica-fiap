from sqlalchemy import func, select

from app.shared.database import get_database_path, get_session
from app.shared.models import CatalogService, Client, Part, ServiceOrder, Vehicle


def get_database_status() -> dict[str, int | str]:
    with get_session() as session:
        total_clients = session.scalar(select(func.count(Client.id))) or 0
        total_vehicles = session.scalar(select(func.count(Vehicle.id))) or 0
        total_services = session.scalar(select(func.count(CatalogService.id))) or 0
        total_parts = session.scalar(select(func.count(Part.id))) or 0
        total_service_orders = session.scalar(select(func.count(ServiceOrder.id))) or 0

    return {
        "database": "sqlite",
        "path": str(get_database_path()),
        "clients": total_clients,
        "vehicles": total_vehicles,
        "services": total_services,
        "parts": total_parts,
        "service_orders": total_service_orders,
    }