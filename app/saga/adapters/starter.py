from sqlalchemy.orm import Session

from app.service_orders.domain.entities import ServiceOrderEntity
from app.service_orders.domain.repository import ISagaStarter
from app.saga.adapters.sqlalchemy_uow import SqlAlchemySagaUnitOfWork
from app.saga.application.orchestrator import SagaOrchestrator


class SessionSagaStarter(ISagaStarter):
    """Inicia a saga usando a sessão (transação) já aberta pela abertura da OS."""

    def __init__(self, session: Session, orchestrator: SagaOrchestrator) -> None:
        self._session = session
        self._orchestrator = orchestrator

    def start(self, order: ServiceOrderEntity) -> None:
        self._orchestrator.start_in(SqlAlchemySagaUnitOfWork(session=self._session), order)
