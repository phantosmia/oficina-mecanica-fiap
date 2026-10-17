from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.shared.models import Client as ClientORM
from app.shared.models import ServiceOrder as ServiceOrderORM
from app.shared.models import ServiceOrderItem as ServiceOrderItemORM
from app.shared.models import ServiceOrderStatusHistory as StatusHistoryORM
from app.shared.models import Vehicle as VehicleORM
from app.service_orders.domain.entities import (
    AverageExecutionTimeData,
    ClientRef,
    OrderItem,
    ServiceOrderEntity,
    StatusChange,
    VehicleRef,
)
from app.service_orders.domain.repository import IServiceOrderRepository
from app.service_orders.domain.value_objects import INACTIVE_STATUSES, ServiceOrderStatus

# Colunas da OS que a saga pode atualizar (OrderChange.fields), além dos itens.
_UPDATABLE_FIELDS = {
    "diagnosis_notes", "labor_total", "parts_total", "quote_total",
    "quote_sent_at", "approved_at", "paid_at", "started_at", "finished_at", "delivered_at", "cancelled_at",
}


def _naive_utc(value: Any) -> Any:
    # As colunas *_at da OS são `DateTime` sem fuso (herança das fases
    # anteriores): grava sempre em UTC, sem tzinfo.
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _to_entity(orm: ServiceOrderORM) -> ServiceOrderEntity:
    return ServiceOrderEntity(
        id=orm.id,
        client_id=orm.client_id,
        vehicle_id=orm.vehicle_id,
        status=orm.status,
        problem_description=orm.problem_description,
        diagnosis_notes=orm.diagnosis_notes,
        labor_total=orm.labor_total,
        parts_total=orm.parts_total,
        quote_total=orm.quote_total,
        client_name=orm.client.name,
        client_document_number=orm.client.document_number or "",
        client_email=orm.client.email,
        vehicle_plate=orm.vehicle.license_plate,
        vehicle_brand=orm.vehicle.brand,
        vehicle_model=orm.vehicle.model,
        vehicle_year=orm.vehicle.year,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        quote_sent_at=orm.quote_sent_at,
        approved_at=orm.approved_at,
        paid_at=orm.paid_at,
        started_at=orm.started_at,
        finished_at=orm.finished_at,
        delivered_at=orm.delivered_at,
        cancelled_at=orm.cancelled_at,
        items=[OrderItem(i.kind, i.item_id, i.name, i.quantity, i.unit_price, i.subtotal) for i in orm.items],
        status_history=[StatusChange(h.from_status, h.to_status, h.reason, h.created_at) for h in orm.status_history],
    )


def _query():  # noqa: ANN202
    return select(ServiceOrderORM).options(
        joinedload(ServiceOrderORM.client),
        joinedload(ServiceOrderORM.vehicle),
        selectinload(ServiceOrderORM.items),
        selectinload(ServiceOrderORM.status_history),
    )


class SqlAlchemyServiceOrderRepository(IServiceOrderRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_client(self, name: str, document_type: str, document_number: str, email: str | None, phone: str | None) -> ClientRef:
        client = self._session.scalar(select(ClientORM).where(ClientORM.document_number == document_number))
        if client is None:
            client = ClientORM(name=name, document_type=document_type, document_number=document_number, email=email, phone=phone)
            self._session.add(client)
        else:
            client.name, client.email, client.phone, client.updated_at = name, email, phone, datetime.now(UTC)
        self._session.flush()
        return ClientRef(id=client.id)

    def upsert_vehicle(self, client_id: int, brand: str, model: str, year: int, plate: str) -> VehicleRef:
        vehicle = self._session.scalar(select(VehicleORM).where(VehicleORM.license_plate == plate))
        if vehicle is None:
            vehicle = VehicleORM(client_id=client_id, brand=brand, model=model, year=year, license_plate=plate)
            self._session.add(vehicle)
        else:
            vehicle.client_id, vehicle.brand, vehicle.model, vehicle.year = client_id, brand, model, year
            vehicle.updated_at = datetime.now(UTC)
        self._session.flush()
        return VehicleRef(id=vehicle.id)

    def create_order(self, client_id: int, vehicle_id: int, problem_description: str, now: datetime) -> ServiceOrderEntity:
        order = ServiceOrderORM(
            client_id=client_id,
            vehicle_id=vehicle_id,
            status=ServiceOrderStatus.RECEIVED.value,
            problem_description=problem_description,
        )
        self._session.add(order)
        self._session.flush()
        self._session.add(
            StatusHistoryORM(service_order_id=order.id, from_status=None, to_status=order.status, reason="OS aberta", created_at=now)
        )
        self._session.flush()
        return self.get_order(order.id)

    def list_active_orders(self) -> list[ServiceOrderEntity]:
        priority = case(
            (ServiceOrderORM.status == ServiceOrderStatus.IN_PROGRESS.value, 1),
            (ServiceOrderORM.status == ServiceOrderStatus.WAITING_PAYMENT.value, 2),
            (ServiceOrderORM.status == ServiceOrderStatus.WAITING_APPROVAL.value, 3),
            (ServiceOrderORM.status == ServiceOrderStatus.IN_DIAGNOSIS.value, 4),
            (ServiceOrderORM.status == ServiceOrderStatus.RECEIVED.value, 5),
            else_=6,
        )
        stmt = _query().where(ServiceOrderORM.status.not_in([s.value for s in INACTIVE_STATUSES])).order_by(priority, ServiceOrderORM.created_at)
        return [_to_entity(o) for o in self._session.scalars(stmt).unique()]

    def get_order(self, order_id: int) -> ServiceOrderEntity | None:
        orm = self._session.scalars(_query().where(ServiceOrderORM.id == order_id).execution_options(populate_existing=True)).unique().first()
        return _to_entity(orm) if orm else None

    def apply_change(
        self, order_id: int, status: ServiceOrderStatus | None, reason: str, fields: dict[str, Any], now: datetime
    ) -> tuple[str, ServiceOrderEntity]:
        order = self._session.get(ServiceOrderORM, order_id, with_for_update=True)
        if order is None:
            raise LookupError(f"OS {order_id} não existe.")
        previous = order.status
        for key, value in fields.items():
            if key == "items":
                order.items.clear()
                order.items.extend(ServiceOrderItemORM(**item) for item in value)
            elif key in _UPDATABLE_FIELDS:
                setattr(order, key, _naive_utc(value))
            else:
                raise ValueError(f"Campo não atualizável na OS: {key}")
        if status is not None and status.value != previous:
            order.status = status.value
            self._session.add(StatusHistoryORM(service_order_id=order_id, from_status=previous, to_status=status.value, reason=reason, created_at=now))
        order.updated_at = _naive_utc(now)
        self._session.flush()
        return previous, self.get_order(order_id)

    def get_tracking(self, order_id: int, document_number: str) -> ServiceOrderEntity | None:
        stmt = _query().join(ServiceOrderORM.client).where(ServiceOrderORM.id == order_id, ClientORM.document_number == document_number)
        orm = self._session.scalars(stmt).unique().first()
        return _to_entity(orm) if orm else None

    def get_average_execution_time(self) -> AverageExecutionTimeData:
        # Execução = do início do reparo (ReparoIniciado) à finalização (ExecucaoFinalizada).
        minutes = func.extract("epoch", ServiceOrderORM.finished_at - ServiceOrderORM.started_at) / 60
        condition = ServiceOrderORM.started_at.is_not(None), ServiceOrderORM.finished_at.is_not(None)
        finished_orders = self._session.scalar(select(func.count(ServiceOrderORM.id)).where(*condition)) or 0
        average_minutes = self._session.scalar(select(func.coalesce(func.avg(minutes), 0)).where(*condition)) or 0
        return AverageExecutionTimeData(finished_orders=int(finished_orders), average_minutes=round(float(average_minutes), 2))

    def commit(self) -> None:
        self._session.commit()
