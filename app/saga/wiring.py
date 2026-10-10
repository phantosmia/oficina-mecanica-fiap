"""Montagem das dependências do orquestrador (usada pela API e pelo worker)."""

from datetime import timedelta

from app.shared.database import get_session_factory
from app.shared.settings import settings
from app.shared.smtp_notifier import SmtpEmailNotifier
from app.saga.adapters.sqlalchemy_uow import SqlAlchemySagaUnitOfWork
from app.saga.application.orchestrator import SagaOrchestrator
from app.saga.domain.value_objects import SagaTimeouts


def saga_timeouts() -> SagaTimeouts:
    return SagaTimeouts(
        reply=timedelta(seconds=settings.saga_reply_timeout_seconds),
        approval=timedelta(seconds=settings.saga_approval_timeout_seconds),
        payment=timedelta(seconds=settings.saga_payment_timeout_seconds),
        max_attempts=settings.saga_max_attempts,
    )


def build_orchestrator() -> SagaOrchestrator:
    return SagaOrchestrator(lambda: SqlAlchemySagaUnitOfWork(get_session_factory()), saga_timeouts(), SmtpEmailNotifier())
