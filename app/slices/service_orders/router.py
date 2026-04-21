from fastapi import APIRouter, Depends, Response, status

from app.shared.dependencies import get_current_admin
from app.slices.service_orders.mapper import (
    to_average_execution_time_model,
    to_read_model,
    to_summary_model,
    to_tracking_model,
)
from app.slices.service_orders.schemas import (
    AverageExecutionTimeRead,
    ServiceOrderCreate,
    ServiceOrderDiagnosisUpdate,
    ServiceOrderQuoteSend,
    ServiceOrderRead,
    ServiceOrderSummary,
    ServiceOrderTracking,
)
from app.slices.service_orders.service import (
    approve_order,
    create_service_order,
    deliver_order,
    finish_order,
    get_average_execution_time,
    get_service_order,
    get_tracking,
    list_service_orders,
    send_quote,
    start_diagnosis,
)


router = APIRouter(prefix="/service-orders", tags=["service-orders"])


@router.get("", response_model=list[ServiceOrderSummary], dependencies=[Depends(get_current_admin)])
def get_orders() -> list[ServiceOrderSummary]:
    return [to_summary_model(item) for item in list_service_orders()]


@router.get("/metrics/average-execution-time", response_model=AverageExecutionTimeRead, dependencies=[Depends(get_current_admin)])
def average_execution_time() -> AverageExecutionTimeRead:
    return to_average_execution_time_model(get_average_execution_time())


@router.get("/{order_id}", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def get_order(order_id: int) -> ServiceOrderRead:
    return to_read_model(get_service_order(order_id))


@router.post("", response_model=ServiceOrderRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
def post_order(payload: ServiceOrderCreate) -> ServiceOrderRead:
    return to_read_model(create_service_order(payload.model_dump()))


@router.post("/{order_id}/diagnosis", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def begin_diagnosis(order_id: int, payload: ServiceOrderDiagnosisUpdate) -> ServiceOrderRead:
    return to_read_model(start_diagnosis(order_id, payload.diagnosis_notes))


@router.post("/{order_id}/send-quote", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def quote_order(order_id: int, payload: ServiceOrderQuoteSend) -> ServiceOrderRead:
    return to_read_model(send_quote(order_id, payload.diagnosis_notes))


@router.post("/{order_id}/approve", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def approve_service_order(order_id: int) -> ServiceOrderRead:
    return to_read_model(approve_order(order_id))


@router.post("/{order_id}/finish", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def finish_service_order(order_id: int) -> ServiceOrderRead:
    return to_read_model(finish_order(order_id))


@router.post("/{order_id}/deliver", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def deliver_service_order(order_id: int) -> ServiceOrderRead:
    return to_read_model(deliver_order(order_id))


@router.get("/{order_id}/tracking", response_model=ServiceOrderTracking)
def track_order(order_id: int, document_number: str) -> ServiceOrderTracking:
    return to_tracking_model(get_tracking(order_id, document_number))
