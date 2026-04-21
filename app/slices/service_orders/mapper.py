from app.shared.models import ServiceOrder
from app.slices.service_orders.schemas import (
    AverageExecutionTimeRead,
    ServiceOrderPartItemRead,
    ServiceOrderRead,
    ServiceOrderServiceItemRead,
    ServiceOrderSummary,
    ServiceOrderTracking,
)


def to_summary_model(order: ServiceOrder) -> ServiceOrderSummary:
    return ServiceOrderSummary(
        id=order.id,
        status=order.status,
        client_name=order.client.name,
        client_document_number=order.client.document_number or "",
        vehicle_plate=order.vehicle.license_plate,
        vehicle_model=order.vehicle.model,
        quote_total=order.quote_total,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def to_read_model(order: ServiceOrder) -> ServiceOrderRead:
    return ServiceOrderRead(
        **to_summary_model(order).model_dump(),
        client_id=order.client_id,
        vehicle_id=order.vehicle_id,
        problem_description=order.problem_description,
        diagnosis_notes=order.diagnosis_notes,
        labor_total=order.labor_total,
        parts_total=order.parts_total,
        quote_sent_at=order.quote_sent_at,
        approved_at=order.approved_at,
        started_at=order.started_at,
        finished_at=order.finished_at,
        delivered_at=order.delivered_at,
        services=[
            ServiceOrderServiceItemRead(
                service_id=item.service_id,
                name=item.service.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            for item in order.service_items
        ],
        parts=[
            ServiceOrderPartItemRead(
                part_id=item.part_id,
                name=item.part.name,
                sku=item.part.sku,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            for item in order.part_items
        ],
    )


def to_tracking_model(order: ServiceOrder) -> ServiceOrderTracking:
    return ServiceOrderTracking(
        id=order.id,
        status=order.status,
        client_name=order.client.name,
        vehicle_plate=order.vehicle.license_plate,
        quote_total=order.quote_total,
        created_at=order.created_at,
        quote_sent_at=order.quote_sent_at,
        approved_at=order.approved_at,
        started_at=order.started_at,
        finished_at=order.finished_at,
        delivered_at=order.delivered_at,
    )


def to_average_execution_time_model(data: dict[str, float | int]) -> AverageExecutionTimeRead:
    return AverageExecutionTimeRead.model_validate(data)
