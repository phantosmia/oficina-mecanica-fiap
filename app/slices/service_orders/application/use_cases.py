from datetime import UTC, datetime

from app.shared.exceptions import InsufficientStockError, NotFoundError
from app.shared.validators import detect_document_type
from app.slices.service_orders.domain.entities import (
    AverageExecutionTimeData,
    PartItemInput,
    ServiceItemInput,
    ServiceOrderEntity,
)
from app.slices.service_orders.domain.repository import IServiceOrderRepository
from app.slices.service_orders.domain.value_objects import ServiceOrderStatus, ensure_transition


class ListServiceOrdersUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self) -> list[ServiceOrderEntity]:
        return self._repo.list_orders()


class GetServiceOrderUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self, order_id: int) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        return order


class CreateServiceOrderUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(
        self,
        client_data: dict,
        vehicle_data: dict,
        problem_description: str,
        requested_services: list[dict],
        requested_parts: list[dict],
    ) -> ServiceOrderEntity:
        document_number = str(client_data["document_number"])
        document_type = detect_document_type(document_number)

        client = self._repo.upsert_client(
            name=str(client_data["name"]),
            document_type=document_type,
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

        service_items: list[ServiceItemInput] = []
        for item in requested_services:
            catalog_service = self._repo.find_active_catalog_service(item["service_id"])
            if catalog_service is None:
                raise NotFoundError("Serviço do catálogo", item["service_id"])
            quantity = int(item["quantity"])
            service_items.append(
                ServiceItemInput(
                    service_id=item["service_id"],
                    quantity=quantity,
                    unit_price=catalog_service.base_price,
                    subtotal=catalog_service.base_price * quantity,
                )
            )

        part_items: list[PartItemInput] = []
        for item in requested_parts:
            part = self._repo.find_part(item["part_id"])
            if part is None:
                raise NotFoundError("Peça/insumo", item["part_id"])
            quantity = int(item["quantity"])
            if part.stock_quantity < quantity:
                raise InsufficientStockError(f"Estoque insuficiente para a peça {part.name}.")
            part_items.append(
                PartItemInput(
                    part_id=item["part_id"],
                    quantity=quantity,
                    unit_price=part.unit_price,
                    subtotal=part.unit_price * quantity,
                )
            )

        labor_total = sum(i.subtotal for i in service_items)
        parts_total = sum(i.subtotal for i in part_items)

        return self._repo.create_order(
            client_id=client.id,
            vehicle_id=vehicle.id,
            problem_description=problem_description,
            service_items=service_items,
            part_items=part_items,
            labor_total=labor_total,
            parts_total=parts_total,
            quote_total=labor_total + parts_total,
        )


class StartDiagnosisUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self, order_id: int, diagnosis_notes: str) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        ensure_transition(ServiceOrderStatus(order.status), ServiceOrderStatus.IN_DIAGNOSIS)
        result = self._repo.update_order_fields(
            order_id,
            {
                "status": ServiceOrderStatus.IN_DIAGNOSIS.value,
                "diagnosis_notes": diagnosis_notes,
                "updated_at": datetime.now(UTC),
            },
        )
        if result is None:
            raise NotFoundError("Ordem de serviço", order_id)
        return result


class SendQuoteUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self, order_id: int, diagnosis_notes: str | None = None) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        ensure_transition(ServiceOrderStatus(order.status), ServiceOrderStatus.WAITING_APPROVAL)
        fields: dict[str, object] = {
            "status": ServiceOrderStatus.WAITING_APPROVAL.value,
            "quote_sent_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        if diagnosis_notes:
            fields["diagnosis_notes"] = diagnosis_notes
        result = self._repo.update_order_fields(order_id, fields)
        if result is None:
            raise NotFoundError("Ordem de serviço", order_id)
        return result


class ApproveOrderUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self, order_id: int) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        ensure_transition(ServiceOrderStatus(order.status), ServiceOrderStatus.IN_PROGRESS)

        # Validate stock for every part before committing anything
        for item in order.part_items:
            part = self._repo.find_part(item.part_id)
            if part is None:
                raise NotFoundError("Peça", item.part_id)
            if part.stock_quantity < item.quantity:
                raise InsufficientStockError(f"Estoque insuficiente para a peça {part.name}.")

        result = self._repo.execute_approval(order_id)
        if result is None:
            raise NotFoundError("Ordem de serviço", order_id)
        return result


class FinishOrderUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self, order_id: int) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        ensure_transition(ServiceOrderStatus(order.status), ServiceOrderStatus.FINISHED)
        result = self._repo.update_order_fields(
            order_id,
            {
                "status": ServiceOrderStatus.FINISHED.value,
                "finished_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        if result is None:
            raise NotFoundError("Ordem de serviço", order_id)
        return result


class DeliverOrderUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self, order_id: int) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        ensure_transition(ServiceOrderStatus(order.status), ServiceOrderStatus.DELIVERED)
        result = self._repo.update_order_fields(
            order_id,
            {
                "status": ServiceOrderStatus.DELIVERED.value,
                "delivered_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        if result is None:
            raise NotFoundError("Ordem de serviço", order_id)
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
