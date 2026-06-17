from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.shared.database import get_safe_database_url
from app.shared.models import CatalogService, Client, Part, ServiceOrder, Vehicle
from app.system.domain.entity import DatabaseStatusEntity
from app.system.domain.repository import ISystemRepository


class SqlAlchemySystemRepository(ISystemRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_database_status(self) -> DatabaseStatusEntity:
        return DatabaseStatusEntity(
            database="postgresql",
            connection=get_safe_database_url(),
            clients=self._session.scalar(select(func.count(Client.id))) or 0,
            vehicles=self._session.scalar(select(func.count(Vehicle.id))) or 0,
            services=self._session.scalar(select(func.count(CatalogService.id))) or 0,
            parts=self._session.scalar(select(func.count(Part.id))) or 0,
            service_orders=self._session.scalar(select(func.count(ServiceOrder.id))) or 0,
        )
