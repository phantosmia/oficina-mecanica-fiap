from datetime import UTC, datetime

from app.shared.exceptions import NotFoundError
from app.shared.telemetry import record_service_order_created, record_service_order_status_changed
from app.shared.validators import detect_document_type
from app.service_orders.domain.entities import AverageExecutionTimeData, ServiceOrderEntity
from app.service_orders.domain.repository import IServiceOrderRepository, ISagaStarter
from app.service_orders.domain.value_objects import ServiceOrderStatus, ensure_can_deliver


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def seconds_between(start: datetime | None, end: datetime | None) -> float | None:
    """end - start em segundos. As colunas *_at da OS são `DateTime` sem fuso
    e voltam "naive" do banco, mas são sempre gravadas em UTC: tratadas como UTC."""
    if start is None or end is None:
        return None
    return (_as_utc(end) - _as_utc(start)).total_seconds()


class ListServiceOrdersUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self) -> list[ServiceOrderEntity]:
        return self._repo.list_active_orders()


class GetServiceOrderUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self, order_id: int) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        return order


class CreateServiceOrderUseCase:
    """Abre a OS com cliente, veículo e problema relatado (ADR-0010: os
    serviços e peças vêm depois, do diagnóstico) e inicia a saga."""

    def __init__(self, repo: IServiceOrderRepository, saga: ISagaStarter) -> None:
        self._repo = repo
        self._saga = saga

    def execute(self, client_data: dict, vehicle_data: dict, problem_description: str) -> ServiceOrderEntity:
        document_number = str(client_data["document_number"])
        client = self._repo.upsert_client(
            name=str(client_data["name"]),
            document_type=detect_document_type(document_number),
            document_number=document_number,
            email=client_data.get("email"),
            phone=client_data.get("phone"),
        )
        vehicle = self._repo.upsert_vehicle(
            client_id=client.id,
            brand=str(vehicle_data["brand"]),
            model=str(vehicle_data["model"]),
            year=int(vehicle_data["year"]),
            plate=str(vehicle_data["plate"]),
        )
        order = self._repo.create_order(client.id, vehicle.id, problem_description, datetime.now(UTC))
        # Mesma transação: ou a OS existe com a saga iniciada (e o primeiro
        # comando na outbox), ou nenhum dos dois.
        self._saga.start(order)
        self._repo.commit()
        record_service_order_created(order_id=order.id, client_id=client.id, quote_total=0.0)
        return order


class DeliverOrderUseCase:
    """Entrega do veículo ao cliente: a única mudança de status feita à mão
    (a saga termina em `finalizada`)."""

    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self, order_id: int) -> ServiceOrderEntity:
        order = GetServiceOrderUseCase(self._repo).execute(order_id)
        ensure_can_deliver(ServiceOrderStatus(order.status))
        now = datetime.now(UTC)
        _, result = self._repo.apply_change(order_id, ServiceOrderStatus.DELIVERED, "veículo entregue ao cliente", {"delivered_at": now}, now)
        self._repo.commit()
        record_service_order_status_changed(
            order_id=order_id,
            from_status=ServiceOrderStatus.FINISHED.value,
            to_status=ServiceOrderStatus.DELIVERED.value,
            seconds_in_previous_status=seconds_between(order.finished_at, now),
        )
        return result


class GetTrackingUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self, order_id: int, document_number: str) -> ServiceOrderEntity:
        order = self._repo.get_tracking(order_id, document_number)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        return order


class GetAverageExecutionTimeUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self) -> AverageExecutionTimeData:
        return self._repo.get_average_execution_time()
