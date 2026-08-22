from datetime import UTC, datetime
from secrets import compare_digest, token_urlsafe

from app.shared.email import (
    IEmailNotifier,
    NullEmailNotifier,
    order_finished_message,
    quote_approved_message,
    quote_available_message,
    quote_rejected_message,
)
from app.shared.exceptions import InsufficientStockError, NotFoundError, PermissionDeniedError
from app.shared.settings import settings
from app.shared.telemetry import record_service_order_created, record_service_order_status_changed
from app.shared.validators import detect_document_type
from app.service_orders.domain.entities import (
    AverageExecutionTimeData,
    PartItemInput,
    ServiceItemInput,
    ServiceOrderEntity,
)
from app.service_orders.domain.repository import IServiceOrderRepository
from app.service_orders.domain.value_objects import ServiceOrderStatus, ensure_transition


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _seconds_since(reference: datetime | None, until: datetime | None) -> float | None:
    """until - reference, em segundos, tolerando timestamps sem timezone.

    As colunas *_at usam `DateTime` sem timezone (ver TimestampMixin em
    app/shared/models.py) e voltam do banco como datetime "naive" — mas
    sempre gravadas via datetime.now(UTC), então tratamos naive como UTC.
    Sem isso, a subtração levanta TypeError (can't subtract offset-naive
    and offset-aware datetimes) sempre que um dos dois lados vier do banco
    e o outro for um datetime.now(UTC) recém-criado (ou vice-versa).
    """
    if reference is None or until is None:
        return None
    return (_as_utc(until) - _as_utc(reference)).total_seconds()


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

        order = self._repo.create_order(
            client_id=client.id,
            vehicle_id=vehicle.id,
            problem_description=problem_description,
            service_items=service_items,
            part_items=part_items,
            labor_total=labor_total,
            parts_total=parts_total,
            quote_total=labor_total + parts_total,
        )
        record_service_order_created(order_id=order.id, client_id=client.id, quote_total=order.quote_total)
        return order


class StartDiagnosisUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self, order_id: int, diagnosis_notes: str) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        previous_status = order.status
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
        record_service_order_status_changed(
            order_id=order_id,
            from_status=previous_status,
            to_status=ServiceOrderStatus.IN_DIAGNOSIS.value,
        )
        return result


class SendQuoteUseCase:
    def __init__(self, repo: IServiceOrderRepository, notifier: IEmailNotifier | None = None) -> None:
        self._repo = repo
        self._notifier = notifier or NullEmailNotifier()

    def execute(self, order_id: int, diagnosis_notes: str | None = None) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        previous_status = order.status
        ensure_transition(ServiceOrderStatus(order.status), ServiceOrderStatus.WAITING_APPROVAL)
        now = datetime.now(UTC)
        # Se veio de IN_DIAGNOSIS, order.updated_at ainda guarda o instante em que
        # StartDiagnosisUseCase marcou a entrada nesse status (nada mais o
        # sobrescreveu desde então) — dá pra calcular quanto tempo a OS passou
        # em diagnóstico sem precisar de uma coluna dedicada pra isso.
        diagnosis_seconds = (
            _seconds_since(order.updated_at, now)
            if previous_status == ServiceOrderStatus.IN_DIAGNOSIS.value
            else None
        )
        fields: dict[str, object] = {
            "status": ServiceOrderStatus.WAITING_APPROVAL.value,
            "quote_token": token_urlsafe(32),
            "quote_sent_at": now,
            "updated_at": now,
        }
        if diagnosis_notes:
            fields["diagnosis_notes"] = diagnosis_notes
        result = self._repo.update_order_fields(order_id, fields)
        if result is None:
            raise NotFoundError("Ordem de serviço", order_id)
        record_service_order_status_changed(
            order_id=order_id,
            from_status=previous_status,
            to_status=ServiceOrderStatus.WAITING_APPROVAL.value,
            seconds_in_previous_status=diagnosis_seconds,
        )
        if result.client_email:
            subject, body = quote_available_message(
                order_id,
                result.quote_total,
                result.quote_token or "",
                settings.public_base_url,
            )
            self._notifier.send(to=result.client_email, subject=subject, body=body)
        return result


class ApproveOrderUseCase:
    def __init__(self, repo: IServiceOrderRepository, notifier: IEmailNotifier | None = None) -> None:
        self._repo = repo
        self._notifier = notifier or NullEmailNotifier()

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
        waiting_approval_seconds = _seconds_since(order.quote_sent_at, result.approved_at)
        record_service_order_status_changed(
            order_id=order_id,
            from_status=ServiceOrderStatus.WAITING_APPROVAL.value,
            to_status=ServiceOrderStatus.IN_PROGRESS.value,
            seconds_in_previous_status=waiting_approval_seconds,
        )
        if result.client_email:
            subject, body = quote_approved_message(order_id)
            self._notifier.send(to=result.client_email, subject=subject, body=body)
        return result


class RejectOrderUseCase:
    def __init__(self, repo: IServiceOrderRepository, notifier: IEmailNotifier | None = None) -> None:
        self._repo = repo
        self._notifier = notifier or NullEmailNotifier()

    def execute(self, order_id: int) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        ensure_transition(ServiceOrderStatus(order.status), ServiceOrderStatus.REJECTED)
        now = datetime.now(UTC)
        result = self._repo.update_order_fields(
            order_id,
            {
                "status": ServiceOrderStatus.REJECTED.value,
                "quote_token": None,
                "updated_at": now,
            },
        )
        if result is None:
            raise NotFoundError("Ordem de serviço", order_id)
        waiting_approval_seconds = _seconds_since(order.quote_sent_at, now)
        record_service_order_status_changed(
            order_id=order_id,
            from_status=ServiceOrderStatus.WAITING_APPROVAL.value,
            to_status=ServiceOrderStatus.REJECTED.value,
            seconds_in_previous_status=waiting_approval_seconds,
        )
        if result.client_email:
            subject, body = quote_rejected_message(order_id)
            self._notifier.send(to=result.client_email, subject=subject, body=body)
        return result


class RespondQuoteUseCase:
    def __init__(self, repo: IServiceOrderRepository, notifier: IEmailNotifier | None = None) -> None:
        self._repo = repo
        self._notifier = notifier or NullEmailNotifier()

    def execute(self, order_id: int, token: str, decision: str) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        if order.quote_token is None or not compare_digest(order.quote_token, token):
            raise PermissionDeniedError("Token do orçamento inválido.")
        if decision == "approve":
            return ApproveOrderUseCase(self._repo, self._notifier).execute(order_id)
        if decision == "reject":
            return RejectOrderUseCase(self._repo, self._notifier).execute(order_id)
        raise PermissionDeniedError("Decisão de orçamento inválida.")


class FinishOrderUseCase:
    def __init__(self, repo: IServiceOrderRepository, notifier: IEmailNotifier | None = None) -> None:
        self._repo = repo
        self._notifier = notifier or NullEmailNotifier()

    def execute(self, order_id: int) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        ensure_transition(ServiceOrderStatus(order.status), ServiceOrderStatus.FINISHED)
        now = datetime.now(UTC)
        result = self._repo.update_order_fields(
            order_id,
            {
                "status": ServiceOrderStatus.FINISHED.value,
                "finished_at": now,
                "updated_at": now,
            },
        )
        if result is None:
            raise NotFoundError("Ordem de serviço", order_id)
        # "Execução" no dashboard exigido — mesma janela que
        # GetAverageExecutionTimeUseCase já calcula via SQL (started_at até
        # finished_at), só que emitida aqui como evento no momento em que
        # acontece, em vez de agregada sob demanda depois.
        execution_seconds = _seconds_since(order.started_at, now)
        record_service_order_status_changed(
            order_id=order_id,
            from_status=ServiceOrderStatus.IN_PROGRESS.value,
            to_status=ServiceOrderStatus.FINISHED.value,
            seconds_in_previous_status=execution_seconds,
        )
        if result.client_email:
            subject, body = order_finished_message(order_id)
            self._notifier.send(to=result.client_email, subject=subject, body=body)
        return result


class DeliverOrderUseCase:
    def __init__(self, repo: IServiceOrderRepository) -> None:
        self._repo = repo

    def execute(self, order_id: int) -> ServiceOrderEntity:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError("Ordem de serviço", order_id)
        ensure_transition(ServiceOrderStatus(order.status), ServiceOrderStatus.DELIVERED)
        now = datetime.now(UTC)
        result = self._repo.update_order_fields(
            order_id,
            {
                "status": ServiceOrderStatus.DELIVERED.value,
                "delivered_at": now,
                "updated_at": now,
            },
        )
        if result is None:
            raise NotFoundError("Ordem de serviço", order_id)
        # "Finalização" no dashboard exigido: tempo entre a OS ficar pronta
        # (finished_at) e ser de fato entregue ao cliente.
        finalization_seconds = _seconds_since(order.finished_at, now)
        record_service_order_status_changed(
            order_id=order_id,
            from_status=ServiceOrderStatus.FINISHED.value,
            to_status=ServiceOrderStatus.DELIVERED.value,
            seconds_in_previous_status=finalization_seconds,
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
