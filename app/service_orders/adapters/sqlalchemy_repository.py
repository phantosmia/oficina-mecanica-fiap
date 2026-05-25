from datetime import UTC, datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.shared.models import (
    CatalogService as CatalogServiceORM,
    Client as ClientORM,
    Part as PartORM,
    ServiceOrder as ServiceOrderORM,
    ServiceOrderPart,
    ServiceOrderService,
    Vehicle as VehicleORM,
)
from app.service_orders.domain.entities import (
    AverageExecutionTimeData,
    CatalogServiceRef,
    ClientRef,
    PartItemEntity,
    PartItemInput,
    PartRef,
    ServiceItemEntity,
    ServiceItemInput,
    ServiceOrderEntity,
    VehicleRef,
)
from app.service_orders.domain.repository import IServiceOrderRepository
from app.service_orders.domain.value_objects import ServiceOrderStatus


def _to_entity(orm: ServiceOrderORM, *, include_items: bool = True) -> ServiceOrderEntity:
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
        vehicle_model=orm.vehicle.model,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        quote_sent_at=orm.quote_sent_at,
        approved_at=orm.approved_at,
        started_at=orm.started_at,
        finished_at=orm.finished_at,
        delivered_at=orm.delivered_at,
        service_items=[
            ServiceItemEntity(
                service_id=item.service_id,
                name=item.service.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            for item in orm.service_items
        ] if include_items else [],
        part_items=[
            PartItemEntity(
                part_id=item.part_id,
                name=item.part.name,
                sku=item.part.sku,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            for item in orm.part_items
        ] if include_items else [],
    )


def _load_full(session: Session, order_id: int) -> ServiceOrderORM | None:
    stmt = (
        select(ServiceOrderORM)
        .options(
            joinedload(ServiceOrderORM.client),
            joinedload(ServiceOrderORM.vehicle),
            selectinload(ServiceOrderORM.service_items).joinedload(ServiceOrderService.service),
            selectinload(ServiceOrderORM.part_items).joinedload(ServiceOrderPart.part),
        )
        .where(ServiceOrderORM.id == order_id)
    )
    return session.execute(stmt).unique().scalar_one_or_none()


class SqlAlchemyServiceOrderRepository(IServiceOrderRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── cross-domain lookups ──────────────────────────────────────────────────

    def upsert_client(
        self,
        name: str,
        document_type: str,
        document_number: str,
        email: str | None,
        phone: str | None,
    ) -> ClientRef:
        existing = self._session.scalar(select(ClientORM).where(ClientORM.document_number == document_number))
        if existing is None:
            client = ClientORM(
                name=name,
                document_type=document_type,
                document_number=document_number,
                email=email,
                phone=phone,
            )
            self._session.add(client)
            self._session.flush()
        else:
            existing.name = name
            existing.email = email
            existing.phone = phone
            existing.updated_at = datetime.now(UTC)
            self._session.flush()
            client = existing
        return ClientRef(id=client.id)

    def upsert_vehicle(self, client_id: int, brand: str, model: str, year: int, plate: str) -> VehicleRef:
        existing = self._session.scalar(select(VehicleORM).where(VehicleORM.license_plate == plate))
        if existing is None:
            vehicle = VehicleORM(client_id=client_id, brand=brand, model=model, year=year, license_plate=plate)
            self._session.add(vehicle)
            self._session.flush()
        else:
            existing.client_id = client_id
            existing.brand = brand
            existing.model = model
            existing.year = year
            existing.updated_at = datetime.now(UTC)
            self._session.flush()
            vehicle = existing
        return VehicleRef(id=vehicle.id)

    def find_active_catalog_service(self, service_id: int) -> CatalogServiceRef | None:
        orm = self._session.scalar(
            select(CatalogServiceORM).where(
                CatalogServiceORM.id == service_id,
                CatalogServiceORM.active.is_(True),
            )
        )
        return CatalogServiceRef(id=orm.id, base_price=orm.base_price) if orm else None

    def find_part(self, part_id: int) -> PartRef | None:
        orm = self._session.get(PartORM, part_id)
        return PartRef(id=orm.id, name=orm.name, unit_price=orm.unit_price, stock_quantity=orm.stock_quantity) if orm else None

    # ── order CRUD ────────────────────────────────────────────────────────────

    def create_order(
        self,
        client_id: int,
        vehicle_id: int,
        problem_description: str,
        service_items: list[ServiceItemInput],
        part_items: list[PartItemInput],
        labor_total: float,
        parts_total: float,
        quote_total: float,
    ) -> ServiceOrderEntity:
        order = ServiceOrderORM(
            client_id=client_id,
            vehicle_id=vehicle_id,
            status=ServiceOrderStatus.RECEIVED.value,
            problem_description=problem_description,
            labor_total=labor_total,
            parts_total=parts_total,
            quote_total=quote_total,
        )
        self._session.add(order)
        self._session.flush()

        for item in service_items:
            self._session.add(
                ServiceOrderService(
                    service_order_id=order.id,
                    service_id=item.service_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                )
            )
        for item in part_items:
            self._session.add(
                ServiceOrderPart(
                    service_order_id=order.id,
                    part_id=item.part_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                )
            )
        self._session.commit()
        return _to_entity(_load_full(self._session, order.id))  # type: ignore[arg-type]

    def list_orders(self) -> list[ServiceOrderEntity]:
        stmt = (
            select(ServiceOrderORM)
            .options(joinedload(ServiceOrderORM.client), joinedload(ServiceOrderORM.vehicle))
            .order_by(ServiceOrderORM.id.desc())
        )
        return [_to_entity(o, include_items=False) for o in self._session.scalars(stmt).all()]

    def list_active_orders(self) -> list[ServiceOrderEntity]:
        _INACTIVE = [
            ServiceOrderStatus.FINISHED.value,
            ServiceOrderStatus.DELIVERED.value,
            ServiceOrderStatus.REJECTED.value,
        ]
        _priority = case(
            (ServiceOrderORM.status == ServiceOrderStatus.IN_PROGRESS.value, 1),
            (ServiceOrderORM.status == ServiceOrderStatus.WAITING_APPROVAL.value, 2),
            (ServiceOrderORM.status == ServiceOrderStatus.IN_DIAGNOSIS.value, 3),
            (ServiceOrderORM.status == ServiceOrderStatus.RECEIVED.value, 4),
            else_=5,
        )
        stmt = (
            select(ServiceOrderORM)
            .options(joinedload(ServiceOrderORM.client), joinedload(ServiceOrderORM.vehicle))
            .where(ServiceOrderORM.status.not_in(_INACTIVE))
            .order_by(_priority, ServiceOrderORM.created_at.asc())
        )
        return [_to_entity(o, include_items=False) for o in self._session.scalars(stmt).unique().all()]

    def get_order(self, order_id: int) -> ServiceOrderEntity | None:
        orm = _load_full(self._session, order_id)
        return _to_entity(orm) if orm else None

    def update_order_fields(self, order_id: int, fields: dict[str, object]) -> ServiceOrderEntity | None:
        order = self._session.get(ServiceOrderORM, order_id)
        if order is None:
            return None
        for key, value in fields.items():
            setattr(order, key, value)
        self._session.commit()
        return _to_entity(_load_full(self._session, order_id))  # type: ignore[arg-type]

    # ── atomic approval ───────────────────────────────────────────────────────

    def execute_approval(self, order_id: int) -> ServiceOrderEntity | None:
        order = self._session.get(ServiceOrderORM, order_id)
        if order is None:
            return None
        full = _load_full(self._session, order_id)
        now = datetime.now(UTC)
        for item in full.part_items:  # type: ignore[union-attr]
            part = self._session.get(PartORM, item.part_id)
            if part is not None:
                part.stock_quantity -= item.quantity
                part.updated_at = now
        order.status = ServiceOrderStatus.IN_PROGRESS.value
        order.approved_at = now
        order.started_at = now
        order.updated_at = now
        self._session.commit()
        return _to_entity(_load_full(self._session, order_id))  # type: ignore[arg-type]

    # ── tracking and metrics ──────────────────────────────────────────────────

    def get_tracking(self, order_id: int, document_number: str) -> ServiceOrderEntity | None:
        stmt = (
            select(ServiceOrderORM)
            .options(joinedload(ServiceOrderORM.client), joinedload(ServiceOrderORM.vehicle))
            .join(ServiceOrderORM.client)
            .where(ServiceOrderORM.id == order_id, ClientORM.document_number == document_number)
        )
        orm = self._session.scalars(stmt).first()
        return _to_entity(orm, include_items=False) if orm else None

    def get_average_execution_time(self) -> AverageExecutionTimeData:
        avg_expr = (
            (func.julianday(ServiceOrderORM.finished_at) - func.julianday(ServiceOrderORM.started_at)) * 24 * 60
        )
        condition = ServiceOrderORM.started_at.is_not(None), ServiceOrderORM.finished_at.is_not(None)
        finished_orders = self._session.scalar(select(func.count(ServiceOrderORM.id)).where(*condition)) or 0
        average_minutes = (
            self._session.scalar(select(func.coalesce(func.avg(avg_expr), 0)).where(*condition)) or 0
        )
        return AverageExecutionTimeData(
            finished_orders=int(finished_orders),
            average_minutes=round(float(average_minutes), 2),
        )
