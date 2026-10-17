"""Orquestrador da saga da OS (ADR-0008): aplica as decisões da máquina de
estados (`ServiceOrderSaga`) dentro de uma transação."""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from app.shared.email import IEmailNotifier, NullEmailNotifier, order_finished_message
from app.shared.events import Envelope
from app.shared.exceptions import NotFoundError
from app.shared.telemetry import record_service_order_status_changed
from app.service_orders.application.use_cases import seconds_between
from app.service_orders.domain.entities import ServiceOrderEntity
from app.saga.domain.ports import ISagaUnitOfWork
from app.saga.domain.saga import Decision, ServiceOrderSaga
from app.saga.domain.value_objects import COMMAND_DESTINATIONS, SagaTimeouts

logger = logging.getLogger(__name__)

# Quando a OS entrou no status anterior, para medir o tempo em cada etapa
# (evento customizado do New Relic, dashboard da Fase 3).
_STATUS_ENTERED_AT = {
    "aguardando_aprovacao": "quote_sent_at",
    "aguardando_pagamento": "approved_at",
    "em_execucao": "paid_at",
    "finalizada": "finished_at",
}


class SagaOrchestrator:
    def __init__(self, uow_factory: Callable[[], ISagaUnitOfWork], timeouts: SagaTimeouts, notifier: IEmailNotifier | None = None) -> None:
        self._uow_factory = uow_factory
        self._timeouts = timeouts
        self._notifier = notifier or NullEmailNotifier()

    # ── início (chamado na transação da abertura da OS) ──────────────────────

    def start_in(self, uow: ISagaUnitOfWork, order: ServiceOrderEntity) -> ServiceOrderSaga:
        saga, decision = ServiceOrderSaga.begin(
            saga_id=str(uuid.uuid4()),
            order_id=order.id,
            customer={"name": order.client_name, "email": order.client_email},
            vehicle={"plate": order.vehicle_plate, "brand": order.vehicle_brand, "model": order.vehicle_model, "year": order.vehicle_year},
            problem_description=order.problem_description,
            now=datetime.now(UTC),
            timeouts=self._timeouts,
        )
        self._send_commands(uow, saga, decision)
        uow.save(saga)
        return saga

    # ── eventos dos participantes ────────────────────────────────────────────

    def handle_event(self, event: Envelope) -> None:
        with self._uow_factory() as uow:
            if not uow.mark_processed(event.message_id, event.type):
                logger.info("evento já processado type=%s message_id=%s", event.type, event.message_id)
                return
            saga = uow.get(event.saga_id, for_update=True) if event.saga_id else None
            if saga is None and event.order_id is not None:
                saga = uow.get_by_order(event.order_id, for_update=True)
            if saga is None:
                logger.warning("evento sem saga correspondente type=%s saga_id=%s order_id=%s", event.type, event.saga_id, event.order_id)
                uow.commit()
                return
            now = datetime.now(UTC)
            decision = saga.handle(event.type, event.payload, now, self._timeouts)
            if decision.ignored:
                logger.info("evento ignorado pela saga %s: %s", saga.id, decision.ignored_reason)
            change = self._apply(uow, saga, decision, now)
            uow.commit()
        self._after_commit(saga, decision, change)

    # ── prazos ───────────────────────────────────────────────────────────────

    def process_deadlines(self, now: datetime | None = None) -> int:
        """Trata as sagas com prazo vencido. Retorna quantas agiram."""
        now = now or datetime.now(UTC)
        with self._uow_factory() as uow:
            due = uow.list_due(now)
        acted = 0
        for saga_id in due:
            try:
                with self._uow_factory() as uow:
                    saga = uow.get(saga_id, for_update=True)
                    decision = saga.on_deadline(now, self._timeouts)
                    if decision.ignored:
                        logger.info("prazo da saga %s: %s", saga_id, decision.ignored_reason)
                    change = self._apply(uow, saga, decision, now)
                    uow.commit()
                self._after_commit(saga, decision, change)
                acted += 0 if decision.ignored else 1
            except Exception:
                logger.exception("falha ao tratar o prazo da saga %s", saga_id)
        return acted

    # ── admin ────────────────────────────────────────────────────────────────

    def get(self, order_id: int) -> ServiceOrderSaga:
        with self._uow_factory() as uow:
            saga = uow.get_by_order(order_id)
        if saga is None:
            raise NotFoundError("Saga da OS", order_id)
        return saga

    def retry(self, order_id: int) -> ServiceOrderSaga:
        """Reenvia o último comando (ex.: compensação parada à espera de intervenção)."""
        with self._uow_factory() as uow:
            saga = uow.get_by_order(order_id, for_update=True)
            if saga is None:
                raise NotFoundError("Saga da OS", order_id)
            decision = saga.retry(datetime.now(UTC), self._timeouts)
            self._apply(uow, saga, decision, datetime.now(UTC))
            uow.commit()
        return saga

    # ── auxiliares ───────────────────────────────────────────────────────────

    def _apply(self, uow: ISagaUnitOfWork, saga: ServiceOrderSaga, decision: Decision, now: datetime) -> tuple[str, ServiceOrderEntity] | None:
        self._send_commands(uow, saga, decision)
        change = None
        if decision.order_change is not None:
            oc = decision.order_change
            change = uow.orders.apply_change(saga.order_id, oc.status, oc.reason, oc.fields, now)
        uow.save(saga)
        return change

    @staticmethod
    def _send_commands(uow: ISagaUnitOfWork, saga: ServiceOrderSaga, decision: Decision) -> None:
        for command in decision.commands:
            envelope = Envelope(type=command.type, payload=command.payload, saga_id=saga.id, order_id=saga.order_id)
            uow.send(envelope, COMMAND_DESTINATIONS[command.type])
            logger.info("comando enviado type=%s saga_id=%s order_id=%s", command.type, saga.id, saga.order_id)

    def _after_commit(self, saga: ServiceOrderSaga, decision: Decision, change: tuple[str, ServiceOrderEntity] | None) -> None:
        if change is not None:
            previous, order = change
            if previous != order.status:
                entered_field = _STATUS_ENTERED_AT.get(previous)
                record_service_order_status_changed(
                    order_id=order.id,
                    from_status=previous,
                    to_status=order.status,
                    seconds_in_previous_status=seconds_between(getattr(order, entered_field), datetime.now(UTC)) if entered_field else None,
                )
            if decision.notify_finished and order.client_email:
                subject, body = order_finished_message(order.id)
                try:
                    self._notifier.send(to=order.client_email, subject=subject, body=body)
                except Exception:
                    logger.exception("falha ao avisar o cliente da OS %s", order.id)
