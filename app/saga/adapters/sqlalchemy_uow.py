from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.shared.events import Envelope
from app.shared.models import OutboxMessage, ProcessedMessage
from app.shared.models import Saga as SagaORM
from app.shared.tracing import current_trace_headers
from app.service_orders.adapters.sqlalchemy_repository import SqlAlchemyServiceOrderRepository
from app.service_orders.domain.value_objects import ServiceOrderStatus
from app.saga.domain.ports import ISagaUnitOfWork
from app.saga.domain.saga import ServiceOrderSaga
from app.saga.domain.value_objects import SagaState


def _to_entity(orm: SagaORM) -> ServiceOrderSaga:
    return ServiceOrderSaga(
        id=orm.id,
        order_id=orm.order_id,
        state=SagaState(orm.state),
        created_at=orm.created_at,
        data=dict(orm.data or {}),
        pending_compensations=list(orm.pending_compensations or []),
        final_status=ServiceOrderStatus(orm.final_status) if orm.final_status else None,
        failure_reason=orm.failure_reason,
        last_command=orm.last_command,
        attempts=orm.attempts,
        deadline_at=orm.deadline_at,
        updated_at=orm.updated_at,
    )


def _json_safe(value: object) -> object:
    """O payload pode carregar datetimes; JSONB precisa de texto."""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class SqlAlchemySagaUnitOfWork(ISagaUnitOfWork):
    """Por padrão abre a própria sessão. Com `session=`, usa uma sessão já
    aberta e não a fecha: é assim que a abertura da OS inicia a saga na mesma
    transação (o commit fica com quem abriu a sessão)."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None, session: Session | None = None) -> None:
        self._session_factory = session_factory
        self._external_session = session
        self._session: Session | None = session
        if session is not None:
            self.orders = SqlAlchemyServiceOrderRepository(session)

    def __enter__(self) -> "SqlAlchemySagaUnitOfWork":
        if self._external_session is None:
            self._session = self._session_factory()
            self.orders = SqlAlchemyServiceOrderRepository(self._session)
        return self

    def __exit__(self, *args: object) -> None:
        if self._external_session is None:
            super().__exit__(*args)
            self.session.close()
            self._session = None

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("Unit of work usada fora de um bloco `with`.")
        return self._session

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def _one(self, *criteria, for_update: bool) -> ServiceOrderSaga | None:  # noqa: ANN002
        query = select(SagaORM).where(*criteria)
        if for_update:
            query = query.with_for_update()
        orm = self.session.scalar(query.execution_options(populate_existing=True))
        return _to_entity(orm) if orm else None

    def get(self, saga_id: str, for_update: bool = False) -> ServiceOrderSaga | None:
        return self._one(SagaORM.id == saga_id, for_update=for_update)

    def get_by_order(self, order_id: int, for_update: bool = False) -> ServiceOrderSaga | None:
        return self._one(SagaORM.order_id == order_id, for_update=for_update)

    def save(self, saga: ServiceOrderSaga) -> None:
        orm = self.session.get(SagaORM, saga.id)
        if orm is None:
            orm = SagaORM(id=saga.id, order_id=saga.order_id, created_at=saga.created_at)
            self.session.add(orm)
        orm.state = saga.state.value
        orm.data = _json_safe(saga.data)
        orm.pending_compensations = list(saga.pending_compensations)
        orm.final_status = saga.final_status.value if saga.final_status else None
        orm.failure_reason = saga.failure_reason
        orm.last_command = _json_safe(saga.last_command)
        orm.attempts = saga.attempts
        orm.deadline_at = saga.deadline_at
        orm.updated_at = saga.updated_at
        self.session.flush()

    def list_due(self, now: datetime, limit: int = 50) -> list[str]:
        return list(
            self.session.scalars(
                select(SagaORM.id).where(SagaORM.deadline_at.is_not(None), SagaORM.deadline_at <= now).order_by(SagaORM.deadline_at).limit(limit)
            )
        )

    def mark_processed(self, message_id: str, message_type: str) -> bool:
        # RETURNING em vez de rowcount: num INSERT pela sessão ORM, o rowcount
        # não indica de forma confiável se a linha foi inserida (SQLAlchemy 2.1).
        result = self.session.execute(
            insert(ProcessedMessage)
            .values(message_id=message_id, message_type=message_type)
            .on_conflict_do_nothing(index_elements=["message_id"])
            .returning(ProcessedMessage.message_id)
        )
        return result.scalar() is not None

    def send(self, envelope: Envelope, destination: str) -> None:
        self.session.add(
            OutboxMessage(
                message_id=envelope.message_id,
                message_type=envelope.type,
                destination=destination,
                envelope=_json_safe(envelope.to_dict()),
                trace_headers=current_trace_headers(),
            )
        )
