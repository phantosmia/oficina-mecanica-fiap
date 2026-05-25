from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.shared.database import get_database_path
from app.shared.models import CatalogService, Client, Part, ServiceOrder, Vehicle
from app.slices.system.domain.entity import DatabaseStatusEntity
from app.slices.system.domain.repository import ISystemRepository


class SqlAlchemySystemRepository(ISystemRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_database_status(self) -> DatabaseStatusEntity:
        return DatabaseStatusEntity(
            database="sqlite",
            path=str(get_database_path()),
            clients=self._session.scalar(select(func.count(Client.id))) or 0,
            vehicles=self._session.scalar(select(func.count(Vehicle.id))) or 0,
            services=self._session.scalar(select(func.count(CatalogService.id))) or 0,
            parts=self._session.scalar(select(func.count(Part.id))) or 0,
            service_orders=self._session.scalar(select(func.count(ServiceOrder.id))) or 0,
        )
