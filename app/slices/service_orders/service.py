from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.shared.database import get_session
from app.shared.models import Client, ServiceOrder, ServiceOrderPart, ServiceOrderService, Vehicle
from app.shared.validators import detect_document_type, validate_document
from app.slices.service_orders import repository
from app.slices.service_orders.schemas import ServiceOrderStatus


ALLOWED_STATUS_TRANSITIONS: dict[ServiceOrderStatus, set[ServiceOrderStatus]] = {
    ServiceOrderStatus.RECEIVED: {ServiceOrderStatus.IN_DIAGNOSIS, ServiceOrderStatus.WAITING_APPROVAL},
    ServiceOrderStatus.IN_DIAGNOSIS: {ServiceOrderStatus.WAITING_APPROVAL},
    ServiceOrderStatus.WAITING_APPROVAL: {ServiceOrderStatus.IN_PROGRESS},
    ServiceOrderStatus.IN_PROGRESS: {ServiceOrderStatus.FINISHED},
    ServiceOrderStatus.FINISHED: {ServiceOrderStatus.DELIVERED},
    ServiceOrderStatus.DELIVERED: set(),
}


def create_service_order(payload: dict[str, object]) -> ServiceOrder:
    with get_session() as session:
        client = _get_or_create_client(session, payload["client"])
        vehicle = _get_or_create_vehicle(session, client.id, payload["vehicle"])
        resolved_services = _resolve_services(session, payload["requested_services"])
        resolved_parts = _resolve_parts(session, payload.get("requested_parts", []), validate_only=True)

        labor_total = sum(item["subtotal"] for item in resolved_services)
        parts_total = sum(item["subtotal"] for item in resolved_parts)
        quote_total = labor_total + parts_total

        order = ServiceOrder(
            client_id=client.id,
            vehicle_id=vehicle.id,
            status=ServiceOrderStatus.RECEIVED.value,
            problem_description=str(payload["problem_description"]),
            labor_total=labor_total,
            parts_total=parts_total,
            quote_total=quote_total,
        )
        session.add(order)
        session.flush()

        for item in resolved_services:
            session.add(
                ServiceOrderService(
                    service_order_id=order.id,
                    service_id=item["service_id"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    subtotal=item["subtotal"],
                )
            )

        for item in resolved_parts:
            session.add(
                ServiceOrderPart(
                    service_order_id=order.id,
                    part_id=item["part_id"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    subtotal=item["subtotal"],
                )
            )

        session.commit()
        return repository.get_order_or_404(session, order.id)


def list_service_orders() -> list[ServiceOrder]:
    with get_session() as session:
        return repository.list_orders(session)


def get_service_order(order_id: int) -> ServiceOrder:
    with get_session() as session:
        return repository.get_order_or_404(session, order_id)


def start_diagnosis(order_id: int, diagnosis_notes: str) -> ServiceOrder:
    return _update_status(order_id, ServiceOrderStatus.IN_DIAGNOSIS, diagnosis_notes=diagnosis_notes)


def send_quote(order_id: int, diagnosis_notes: str | None = None) -> ServiceOrder:
    with get_session() as session:
        order = repository.get_order_or_404(session, order_id)
        _ensure_transition(ServiceOrderStatus(order.status), ServiceOrderStatus.WAITING_APPROVAL)

        if diagnosis_notes:
            order.diagnosis_notes = diagnosis_notes

        order.status = ServiceOrderStatus.WAITING_APPROVAL.value
        order.quote_sent_at = datetime.now(UTC)
        order.updated_at = datetime.now(UTC)
        session.commit()
        return repository.get_order_or_404(session, order_id)


def approve_order(order_id: int) -> ServiceOrder:
    with get_session() as session:
        order = repository.get_order_or_404(session, order_id)
        _ensure_transition(ServiceOrderStatus(order.status), ServiceOrderStatus.IN_PROGRESS)

        for item in order.part_items:
            part = repository.find_part(session, item.part_id)
            if part is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Peça vinculada não encontrada.")
            if part.stock_quantity < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Estoque insuficiente para a peça {part.name}.",
                )

        now = datetime.now(UTC)
        for item in order.part_items:
            part = repository.find_part(session, item.part_id)
            if part is not None:
                part.stock_quantity -= item.quantity
                part.updated_at = now
        order.status = ServiceOrderStatus.IN_PROGRESS.value
        order.approved_at = now
        order.started_at = now
        order.updated_at = now
        session.commit()
        return repository.get_order_or_404(session, order_id)


def finish_order(order_id: int) -> ServiceOrder:
    return _update_status(order_id, ServiceOrderStatus.FINISHED, set_finished=True)


def deliver_order(order_id: int) -> ServiceOrder:
    return _update_status(order_id, ServiceOrderStatus.DELIVERED, set_delivered=True)


def get_tracking(order_id: int, document_number: str) -> ServiceOrder:
    with get_session() as session:
        return repository.fetch_tracking(session, order_id, validate_document(document_number))


def get_average_execution_time() -> dict[str, float | int]:
    with get_session() as session:
        return repository.fetch_average_execution_time(session)


def _update_status(
    order_id: int,
    new_status: ServiceOrderStatus,
    *,
    diagnosis_notes: str | None = None,
    set_finished: bool = False,
    set_delivered: bool = False,
) -> ServiceOrder:
    with get_session() as session:
        order = repository.get_order_or_404(session, order_id)
        current_status = ServiceOrderStatus(order.status)
        _ensure_transition(current_status, new_status)

        order.status = new_status.value
        order.updated_at = datetime.now(UTC)

        if diagnosis_notes:
            order.diagnosis_notes = diagnosis_notes
        if set_finished:
            order.finished_at = datetime.now(UTC)
        if set_delivered:
            order.delivered_at = datetime.now(UTC)

        session.commit()
        return repository.get_order_or_404(session, order_id)


def _ensure_transition(current_status: ServiceOrderStatus, new_status: ServiceOrderStatus) -> None:
    if new_status not in ALLOWED_STATUS_TRANSITIONS[current_status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Não é possível alterar o status de {current_status.value} para {new_status.value}.",
        )


def _get_or_create_client(session, payload: dict[str, object]) -> Client:
    document_number = validate_document(str(payload["document_number"]))
    current = repository.find_client_by_document(session, document_number)
    document_type = detect_document_type(document_number)

    if current is None:
        client = Client(
            name=str(payload["name"]),
            document_type=document_type,
            document_number=document_number,
            email=payload.get("email"),
            phone=payload.get("phone"),
        )
        session.add(client)
        session.flush()
        return client

    current.name = str(payload["name"])
    current.email = payload.get("email")
    current.phone = payload.get("phone")
    current.updated_at = datetime.now(UTC)
    session.flush()
    return current


def _get_or_create_vehicle(session, client_id: int, payload: dict[str, object]) -> Vehicle:
    current = repository.find_vehicle_by_plate(session, str(payload["plate"]))

    if current is None:
        vehicle = Vehicle(
            client_id=client_id,
            brand=str(payload["brand"]),
            model=str(payload["model"]),
            year=int(payload["year"]),
            license_plate=str(payload["plate"]),
        )
        session.add(vehicle)
        session.flush()
        return vehicle

    current.client_id = client_id
    current.brand = str(payload["brand"])
    current.model = str(payload["model"])
    current.year = int(payload["year"])
    current.updated_at = datetime.now(UTC)
    session.flush()
    return current


def _resolve_services(session, requested_services: list[dict[str, int]]) -> list[dict[str, object]]:
    resolved: list[dict[str, object]] = []
    for item in requested_services:
        service = repository.find_catalog_service(session, item["service_id"])
        if service is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço do catálogo não encontrado ou inativo.")
        resolved.append(
            {
                "service_id": item["service_id"],
                "quantity": item["quantity"],
                "unit_price": float(service.base_price),
                "subtotal": float(service.base_price) * item["quantity"],
            }
        )
    return resolved


def _resolve_parts(session, requested_parts: list[dict[str, int]], *, validate_only: bool) -> list[dict[str, object]]:
    resolved: list[dict[str, object]] = []
    for item in requested_parts:
        part = repository.find_part(session, item["part_id"])
        if part is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Peça/insumo não encontrado.")
        if validate_only and part.stock_quantity < item["quantity"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Estoque insuficiente para a peça {part.name}.",
            )
        resolved.append(
            {
                "part_id": item["part_id"],
                "quantity": item["quantity"],
                "unit_price": float(part.unit_price),
                "subtotal": float(part.unit_price) * item["quantity"],
            }
        )
    return resolved
