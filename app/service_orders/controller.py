from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.dependencies import get_current_admin, get_current_client
from app.shared.http_errors import domain_error_handler
from app.shared.validators import validate_document
from app.service_orders.adapters.presenter import to_average_execution_time, to_read, to_summary, to_tracking
from app.service_orders.adapters.sqlalchemy_repository import SqlAlchemyServiceOrderRepository
from app.service_orders.application.use_cases import (
    CreateServiceOrderUseCase,
    DeliverOrderUseCase,
    GetAverageExecutionTimeUseCase,
    GetServiceOrderUseCase,
    GetTrackingUseCase,
    ListServiceOrdersUseCase,
)
from app.service_orders.domain.repository import IServiceOrderRepository
from app.service_orders.schemas import (
    AverageExecutionTimeRead,
    SagaRead,
    ServiceOrderCreate,
    ServiceOrderRead,
    ServiceOrderSummary,
    ServiceOrderTracking,
)
from app.saga.adapters.starter import SessionSagaStarter
from app.saga.application.orchestrator import SagaOrchestrator
from app.saga.domain.saga import ServiceOrderSaga
from app.saga.wiring import build_orchestrator

router = APIRouter(prefix="/service-orders", tags=["service-orders"])


def _get_repo(session: Session = Depends(get_db)) -> IServiceOrderRepository:
    return SqlAlchemyServiceOrderRepository(session)


def get_orchestrator() -> SagaOrchestrator:
    return build_orchestrator()


def _saga_read(saga: ServiceOrderSaga) -> SagaRead:
    return SagaRead(
        saga_id=saga.id,
        order_id=saga.order_id,
        state=saga.state.value,
        pending_compensations=saga.pending_compensations,
        final_status=saga.final_status.value if saga.final_status else None,
        failure_reason=saga.failure_reason,
        waiting_for=saga.last_command["type"] if saga.last_command else None,
        attempts=saga.attempts,
        deadline_at=saga.deadline_at,
        data=saga.data,
        created_at=saga.created_at,
        updated_at=saga.updated_at,
    )


@router.get("", response_model=list[ServiceOrderSummary], dependencies=[Depends(get_current_admin)])
def get_orders(repo: IServiceOrderRepository = Depends(_get_repo)) -> list[ServiceOrderSummary]:
    """OS com trabalho pendente, por prioridade de status e depois as mais antigas."""
    return [to_summary(o) for o in ListServiceOrdersUseCase(repo).execute()]


@router.get("/metrics/average-execution-time", response_model=AverageExecutionTimeRead, dependencies=[Depends(get_current_admin)])
def average_execution_time(repo: IServiceOrderRepository = Depends(_get_repo)) -> AverageExecutionTimeRead:
    return to_average_execution_time(GetAverageExecutionTimeUseCase(repo).execute())


@router.get("/{order_id}", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def get_order(order_id: int, repo: IServiceOrderRepository = Depends(_get_repo)) -> ServiceOrderRead:
    with domain_error_handler():
        return to_read(GetServiceOrderUseCase(repo).execute(order_id))


@router.post("", response_model=ServiceOrderRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
def post_order(
    payload: ServiceOrderCreate,
    session: Session = Depends(get_db),
    orchestrator: SagaOrchestrator = Depends(get_orchestrator),
) -> ServiceOrderRead:
    """Abre a OS e inicia a saga (o primeiro passo é a fila de diagnóstico da Execução)."""
    repo = SqlAlchemyServiceOrderRepository(session)
    with domain_error_handler():
        order = CreateServiceOrderUseCase(repo, SessionSagaStarter(session, orchestrator)).execute(
            client_data=payload.client.model_dump(),
            vehicle_data=payload.vehicle.model_dump(),
            problem_description=payload.problem_description,
        )
        return to_read(order)


@router.post("/{order_id}/deliver", response_model=ServiceOrderRead, dependencies=[Depends(get_current_admin)])
def deliver_service_order(order_id: int, repo: IServiceOrderRepository = Depends(_get_repo)) -> ServiceOrderRead:
    """Entrega do veículo: única mudança manual de status (de `finalizada` para `entregue`)."""
    with domain_error_handler():
        return to_read(DeliverOrderUseCase(repo).execute(order_id))


@router.get("/{order_id}/saga", response_model=SagaRead, dependencies=[Depends(get_current_admin)])
def get_saga(order_id: int, orchestrator: SagaOrchestrator = Depends(get_orchestrator)) -> SagaRead:
    """Estado da saga: etapa, compensações pendentes, tentativas, prazo e dados acumulados."""
    with domain_error_handler():
        return _saga_read(orchestrator.get(order_id))


@router.post("/{order_id}/saga/retry", response_model=SagaRead, dependencies=[Depends(get_current_admin)])
def retry_saga(order_id: int, orchestrator: SagaOrchestrator = Depends(get_orchestrator)) -> SagaRead:
    """Reenvia o último comando da saga (ex.: compensação parada à espera de intervenção)."""
    with domain_error_handler():
        return _saga_read(orchestrator.retry(order_id))


@router.get("/{order_id}/tracking", response_model=ServiceOrderTracking)
def track_order(
    order_id: int,
    document_number: str | None = None,
    client: dict[str, str] | None = Depends(get_current_client),
    repo: IServiceOrderRepository = Depends(_get_repo),
) -> ServiceOrderTracking:
    # Aceita duas credenciais equivalentes (RFC-0003 + ADR-0004): o JWT de
    # cliente emitido pela Lambda de autenticação via CPF, se enviado via
    # `Authorization: Bearer`, tem prioridade sobre o `document_number` da
    # query — mantendo o mecanismo público original funcionando sem quebra
    # para quem ainda não migrou para o token.
    resolved_document = client["document_number"] if client is not None else document_number
    if not resolved_document:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe document_number ou um token Bearer válido (emitido pela Lambda de autenticação via CPF).",
        )

    with domain_error_handler():
        return to_tracking(GetTrackingUseCase(repo).execute(order_id, validate_document(resolved_document)))
