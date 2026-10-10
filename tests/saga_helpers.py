"""Apoio aos testes do orquestrador: abrir OS pela API e simular os
participantes publicando eventos."""

from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.shared.database import get_session_factory
from app.shared.email import IEmailNotifier
from app.shared.events import Envelope
from app.saga.adapters.sqlalchemy_uow import SqlAlchemySagaUnitOfWork
from app.saga.application.orchestrator import SagaOrchestrator
from app.saga.domain.value_objects import SagaTimeouts

TIMEOUTS = SagaTimeouts(reply=timedelta(minutes=5), approval=timedelta(days=7), payment=timedelta(days=4), max_attempts=3)

DIAGNOSIS = {
    "notes": "Óleo vencido e filtro saturado",
    "services": [{"service_id": "svc-oleo", "name": "Troca de óleo", "quantity": 1, "unit_price": 150.0, "subtotal": 150.0}],
    "parts": [
        {"part_id": "part-oleo", "name": "Óleo 5W30", "quantity": 4, "unit_price": 45.0, "subtotal": 180.0},
        {"part_id": "part-filtro", "name": "Filtro de óleo", "quantity": 1, "unit_price": 25.5, "subtotal": 25.5},
    ],
    "labor_total": 150.0,
    "parts_total": 205.5,
    "total": 355.5,
}

ORDER_INPUT = {
    "client": {"name": "Maria Souza", "document_number": "529.982.247-25", "email": "maria@example.com"},
    "vehicle": {"plate": "BRA2E19", "brand": "VW", "model": "Gol", "year": 2018},
    "problem_description": "Luz do óleo acendendo no painel",
}


def make_orchestrator(notifier: IEmailNotifier | None = None, timeouts: SagaTimeouts = TIMEOUTS) -> SagaOrchestrator:
    return SagaOrchestrator(lambda: SqlAlchemySagaUnitOfWork(get_session_factory()), timeouts, notifier)


def open_order(client: TestClient, admin_headers: dict[str, str], **overrides: Any) -> dict:
    response = client.post("/service-orders", json={**ORDER_INPUT, **overrides}, headers=admin_headers)
    assert response.status_code == 201, response.text
    return response.json()


class Participants:
    """Faz o papel de Estoque, Execução, Orçamento e Pagamento: publica, para
    o orquestrador, o evento que cada um publicaria."""

    def __init__(self, orchestrator: SagaOrchestrator, order_id: int) -> None:
        self.orchestrator = orchestrator
        self.order_id = order_id
        self.saga_id = orchestrator.get(order_id).id

    def emit(self, event_type: str, **payload: Any) -> Envelope:
        event = Envelope(type=event_type, payload=payload, saga_id=self.saga_id, order_id=self.order_id)
        self.orchestrator.handle_event(event)
        return event

    def until_quote_approved(self) -> None:
        self.emit("DiagnosticoEnfileirado")
        self.emit("DiagnosticoIniciado")
        self.emit("DiagnosticoConcluido", **DIAGNOSIS)
        self.emit("PecasReservadas", reservation_id="res-1", items=[{"part_id": "part-oleo", "quantity": 4}])
        self.emit("OrcamentoGerado", quote_id="q-1", total=355.5)
        self.emit("OrcamentoAprovado", quote_id="q-1", total=355.5, decided_by="cliente")

    def until_paid(self) -> None:
        self.until_quote_approved()
        self.emit("CobrancaCriada", charge_id="c-1", checkout_url="https://mp.test/checkout/c-1", amount=355.5)
        self.emit("PagamentoConfirmado", charge_id="c-1", amount=355.5)
