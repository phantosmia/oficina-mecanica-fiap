from app.service_orders.domain.entities import AverageExecutionTimeData, ServiceOrderEntity
from app.service_orders.schemas import (
    AverageExecutionTimeRead,
    ServiceOrderPartItemRead,
    ServiceOrderRead,
    ServiceOrderServiceItemRead,
    ServiceOrderSummary,
    ServiceOrderTracking,
)


def to_summary(entity: ServiceOrderEntity) -> ServiceOrderSummary:
    return ServiceOrderSummary(
        id=entity.id,
        status=entity.status,
        client_name=entity.client_name,
        client_document_number=entity.client_document_number,
        vehicle_plate=entity.vehicle_plate,
        vehicle_model=entity.vehicle_model,
        quote_total=entity.quote_total,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def to_read(entity: ServiceOrderEntity) -> ServiceOrderRead:
    return ServiceOrderRead(
        **to_summary(entity).model_dump(),
        client_id=entity.client_id,
        vehicle_id=entity.vehicle_id,
        problem_description=entity.problem_description,
        diagnosis_notes=entity.diagnosis_notes,
        labor_total=entity.labor_total,
        parts_total=entity.parts_total,
        quote_sent_at=entity.quote_sent_at,
        approved_at=entity.approved_at,
        started_at=entity.started_at,
        finished_at=entity.finished_at,
        delivered_at=entity.delivered_at,
        services=[
            ServiceOrderServiceItemRead(
                service_id=item.service_id,
                name=item.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            for item in entity.service_items
        ],
        parts=[
            ServiceOrderPartItemRead(
                part_id=item.part_id,
                name=item.name,
                sku=item.sku,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            for item in entity.part_items
        ],
    )


def to_tracking(entity: ServiceOrderEntity) -> ServiceOrderTracking:
    return ServiceOrderTracking(
        id=entity.id,
        status=entity.status,
        client_name=entity.client_name,
        vehicle_plate=entity.vehicle_plate,
        quote_total=entity.quote_total,
        created_at=entity.created_at,
        quote_sent_at=entity.quote_sent_at,
        approved_at=entity.approved_at,
        started_at=entity.started_at,
        finished_at=entity.finished_at,
        delivered_at=entity.delivered_at,
    )


def to_average_execution_time(data: AverageExecutionTimeData) -> AverageExecutionTimeRead:
    return AverageExecutionTimeRead(
        finished_orders=data.finished_orders,
        average_minutes=data.average_minutes,
    )
