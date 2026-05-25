from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.dependencies import get_current_admin
from app.shared.http_errors import domain_error_handler
from app.shared.validators import validate_document
from app.slices.service_orders.adapters.presenter import (
    to_average_execution_time,
    to_read,
    to_summary,
    to_tracking,
)
from app.slices.service_orders.adapters.sqlalchemy_repository import SqlAlchemyServiceOrderRepository
from app.slices.service_orders.application.use_cases import (
    ApproveOrderUseCase,
    CreateServiceOrderUseCase,
    DeliverOrderUseCase,
    FinishOrderUseCase,
    GetAverageExecutionTimeUseCase,
    GetServiceOrderUseCase,
    GetTrackingUseCase,
    ListServiceOrdersUseCase,
    SendQuoteUseCase,
    StartDiagnosisUseCase,
)
from app.slices.service_orders.domain.repository import IServiceOrderRepository
from app.slices.service_orders.schemas import (
    AverageExecutionTimeRead,
    ServiceOrderCreate,
    ServiceOrderDiagnosisUpdate,
    ServiceOrderQuoteSend,
    ServiceOrderRead,
    ServiceOrderSummary,
    ServiceOrderTracking,
)

router = APIRouter(prefix="/service-orders", tags=["service-orders"])


def _get_repo(session: Session = Depends(get_db)) -> IServiceOrderRepository:
    return SqlAlchemyServiceOrderRepository(session)


@router.get("", response_model=list[ServiceOrderSummary], dependencies=[Depends(get_current_admin)])
def get_orders(repo: IServiceOrderRepository = Depends(_get_repo)) -> list[ServiceOrderSummary]:
    return [to_summary(o) for o in ListServiceOrdersUseCase(repo).execute()]


@router.get(
    "/metrics/average-execution-time",
    response_model=AverageExecutionTimeRead,
    dependencies=[Depends(get_current_admin)],
)
def average_execution_time(repo: IServiceOrderRepository = Depends(_get_repo)) -> AverageExecutionTimeRead:
    return to_average_execution_time(GetAverageExecutionTimeUseCase(repo).execute())


@router.get("/{order_id}", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def get_order(order_id: int, repo: IServiceOrderRepository = Depends(_get_repo)) -> ServiceOrderRead:
    with domain_error_handler():
        return to_read(GetServiceOrderUseCase(repo).execute(order_id))


@router.post(
    "",
    response_model=ServiceOrderRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_admin)],
)
def post_order(payload: ServiceOrderCreate, repo: IServiceOrderRepository = Depends(_get_repo)) -> ServiceOrderRead:
    with domain_error_handler():
        return to_read(
            CreateServiceOrderUseCase(repo).execute(
                client_data=payload.client.model_dump(),
                vehicle_data=payload.vehicle.model_dump(),
                problem_description=payload.problem_description,
                requested_services=[i.model_dump() for i in payload.requested_services],
                requested_parts=[i.model_dump() for i in payload.requested_parts],
            )
        )


@router.post("/{order_id}/diagnosis", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def begin_diagnosis(
    order_id: int,
    payload: ServiceOrderDiagnosisUpdate,
    repo: IServiceOrderRepository = Depends(_get_repo),
) -> ServiceOrderRead:
    with domain_error_handler():
        return to_read(StartDiagnosisUseCase(repo).execute(order_id, payload.diagnosis_notes))


@router.post("/{order_id}/send-quote", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def quote_order(
    order_id: int,
    payload: ServiceOrderQuoteSend,
    repo: IServiceOrderRepository = Depends(_get_repo),
) -> ServiceOrderRead:
    with domain_error_handler():
        return to_read(SendQuoteUseCase(repo).execute(order_id, payload.diagnosis_notes))


@router.post("/{order_id}/approve", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def approve_service_order(order_id: int, repo: IServiceOrderRepository = Depends(_get_repo)) -> ServiceOrderRead:
    with domain_error_handler():
        return to_read(ApproveOrderUseCase(repo).execute(order_id))


@router.post("/{order_id}/finish", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def finish_service_order(order_id: int, repo: IServiceOrderRepository = Depends(_get_repo)) -> ServiceOrderRead:
    with domain_error_handler():
        return to_read(FinishOrderUseCase(repo).execute(order_id))


@router.post("/{order_id}/deliver", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def deliver_service_order(order_id: int, repo: IServiceOrderRepository = Depends(_get_repo)) -> ServiceOrderRead:
    with domain_error_handler():
        return to_read(DeliverOrderUseCase(repo).execute(order_id))


@router.get("/{order_id}/tracking", response_model=ServiceOrderTracking)
def track_order(
    order_id: int,
    document_number: str,
    repo: IServiceOrderRepository = Depends(_get_repo),
) -> ServiceOrderTracking:
    with domain_error_handler():
        return to_tracking(GetTrackingUseCase(repo).execute(order_id, validate_document(document_number)))
