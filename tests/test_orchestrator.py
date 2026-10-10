"""O orquestrador com banco de verdade: transação única, idempotência,
mensagens de saga desconhecida, prazos e reenvio manual."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.shared.events import Envelope
from app.saga.domain.value_objects import SagaState
from tests.conftest import FakeNotifier, outbox
from tests.saga_helpers import Participants, make_orchestrator, open_order


def test_full_flow_commands_and_finished_email(client: TestClient, admin_headers: dict[str, str]) -> None:
    notifier = FakeNotifier()
    orchestrator = make_orchestrator(notifier)
    order = open_order(client, admin_headers)
    participants = Participants(orchestrator, order["id"])

    participants.until_paid()
    for event in ("BaixaConfirmada", "ReparoEnfileirado", "ReparoIniciado", "ExecucaoFinalizada"):
        participants.emit(event)

    assert [(c["destination"], c["type"]) for c in outbox()] == [
        ("execucao", "EnfileirarDiagnostico"),
        ("estoque", "ReservarPecas"),
        ("orcamento", "GerarOrcamento"),
        ("pagamento", "CriarCobranca"),
        ("estoque", "ConfirmarBaixa"),
        ("execucao", "EnfileirarReparo"),
    ]
    assert all(c["saga_id"] == participants.saga_id and c["order_id"] == order["id"] for c in outbox())
    final = client.get(f"/service-orders/{order['id']}", headers=admin_headers).json()
    assert final["status"] == "finalizada" and final["paid_at"] and final["started_at"] and final["finished_at"]
    assert orchestrator.get(order["id"]).state == SagaState.COMPLETED
    assert notifier.sent[-1].subject.startswith(f"[OS #{order['id']}] Serviço finalizado")


def test_duplicate_event_is_processed_once(client: TestClient, admin_headers: dict[str, str]) -> None:
    orchestrator = make_orchestrator()
    order = open_order(client, admin_headers)
    participants = Participants(orchestrator, order["id"])
    participants.emit("DiagnosticoEnfileirado")
    event = participants.emit("DiagnosticoConcluido", notes="x", services=[{"service_id": "s", "name": "S", "quantity": 1, "unit_price": 10.0}], parts=[])

    orchestrator.handle_event(event)  # reentrega

    assert [c["type"] for c in outbox()].count("ReservarPecas") == 1


def test_event_without_saga_is_ignored(client: TestClient, admin_headers: dict[str, str]) -> None:
    make_orchestrator().handle_event(Envelope(type="PecasReservadas", payload={}, saga_id="nao-existe", order_id=9999))
    assert outbox() == []


def test_event_found_by_order_when_saga_id_missing(client: TestClient, admin_headers: dict[str, str]) -> None:
    orchestrator = make_orchestrator()
    order = open_order(client, admin_headers)
    orchestrator.handle_event(Envelope(type="DiagnosticoIniciado", payload={}, saga_id=None, order_id=order["id"]))
    assert client.get(f"/service-orders/{order['id']}", headers=admin_headers).json()["status"] == "em_diagnostico"


def test_compensation_flow_ends_rejected(client: TestClient, admin_headers: dict[str, str]) -> None:
    orchestrator = make_orchestrator()
    order = open_order(client, admin_headers)
    participants = Participants(orchestrator, order["id"])
    participants.emit("DiagnosticoEnfileirado")
    participants.emit("DiagnosticoConcluido", notes="x", services=[{"service_id": "s", "name": "S", "quantity": 1, "unit_price": 10.0}], parts=[])
    participants.emit("PecasReservadas", reservation_id="r")
    participants.emit("OrcamentoGerado", quote_id="q")
    participants.emit("OrcamentoRecusado", quote_id="q", decided_by="cliente")

    assert outbox()[-1]["type"] == "LiberarPecas"
    assert client.get(f"/service-orders/{order['id']}", headers=admin_headers).json()["status"] == "aguardando_aprovacao"

    participants.emit("PecasLiberadas")
    body = client.get(f"/service-orders/{order['id']}", headers=admin_headers).json()
    assert body["status"] == "recusada" and body["cancelled_at"] is not None
    assert body["status_history"][-1]["reason"] == "orçamento recusado (cliente)"


def test_deadlines_resend_then_compensate(client: TestClient, admin_headers: dict[str, str]) -> None:
    orchestrator = make_orchestrator()
    order = open_order(client, admin_headers)
    participants = Participants(orchestrator, order["id"])
    participants.emit("DiagnosticoEnfileirado")
    participants.emit("DiagnosticoConcluido", notes="x", services=[{"service_id": "s", "name": "S", "quantity": 1, "unit_price": 10.0}], parts=[])

    now = datetime.now(UTC)
    assert orchestrator.process_deadlines(now) == 0  # ainda no prazo
    for minutes in (6, 12):
        assert orchestrator.process_deadlines(now + timedelta(minutes=minutes)) == 1
    assert [c["type"] for c in outbox()].count("ReservarPecas") == 3  # original + 2 reenvios

    orchestrator.process_deadlines(now + timedelta(minutes=18))  # esgotou: compensa
    saga = orchestrator.get(order["id"])
    assert (saga.state, saga.pending_compensations) == (SagaState.COMPENSATING, ["LiberarPecas"])
    assert outbox()[-1]["type"] == "LiberarPecas"


def test_approval_deadline_cancels_the_order(client: TestClient, admin_headers: dict[str, str]) -> None:
    orchestrator = make_orchestrator()
    order = open_order(client, admin_headers)
    participants = Participants(orchestrator, order["id"])
    participants.emit("DiagnosticoEnfileirado")
    participants.emit("DiagnosticoConcluido", notes="x", services=[{"service_id": "s", "name": "S", "quantity": 1, "unit_price": 10.0}], parts=[])
    participants.emit("PecasReservadas", reservation_id="r")
    participants.emit("OrcamentoGerado", quote_id="q")

    orchestrator.process_deadlines(datetime.now(UTC) + timedelta(days=8))
    participants.emit("OrcamentoCancelado")
    participants.emit("PecasLiberadas")

    body = client.get(f"/service-orders/{order['id']}", headers=admin_headers).json()
    assert body["status"] == "cancelada"
    assert body["status_history"][-1]["reason"] == "prazo de aprovação do orçamento expirado"


def test_manual_retry_of_stuck_compensation(client: TestClient, admin_headers: dict[str, str]) -> None:
    orchestrator = make_orchestrator()
    order = open_order(client, admin_headers)
    participants = Participants(orchestrator, order["id"])
    participants.emit("DiagnosticoEnfileirado")
    participants.emit("DiagnosticoConcluido", notes="x", services=[{"service_id": "s", "name": "S", "quantity": 1, "unit_price": 10.0}], parts=[])
    participants.emit("ReservaRecusada", reason="estoque_insuficiente")  # sem compensação: cancela direto
    assert client.get(f"/service-orders/{order['id']}", headers=admin_headers).json()["status"] == "cancelada"

    second = open_order(client, admin_headers)
    p2 = Participants(orchestrator, second["id"])
    p2.emit("DiagnosticoEnfileirado")
    p2.emit("DiagnosticoConcluido", notes="x", services=[{"service_id": "s", "name": "S", "quantity": 1, "unit_price": 10.0}], parts=[])
    p2.emit("PecasReservadas", reservation_id="r")
    p2.emit("OrcamentoGerado", quote_id="q")
    p2.emit("OrcamentoRecusado")
    now = datetime.now(UTC)
    for minutes in (6, 12, 18):
        orchestrator.process_deadlines(now + timedelta(minutes=minutes))
    stuck = client.get(f"/service-orders/{second['id']}/saga", headers=admin_headers).json()
    assert (stuck["state"], stuck["deadline_at"]) == ("COMPENSANDO", None)
    assert "aguardando intervenção" in stuck["failure_reason"]

    retried = client.post(f"/service-orders/{second['id']}/saga/retry", headers=admin_headers).json()
    assert (retried["waiting_for"], retried["attempts"]) == ("LiberarPecas", 1)
    assert outbox()[-1]["type"] == "LiberarPecas"
