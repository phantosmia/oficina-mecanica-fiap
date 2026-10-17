"""Passos do BDD (tests/features/fluxo_ordem_de_servico.feature).

A OS é aberta e entregue pela API de verdade (com PostgreSQL); os
participantes (Execução, Estoque, Orçamento, Pagamento) são simulados
publicando ao orquestrador os eventos que publicariam. Os comandos
enviados são lidos da outbox, que é o que vai para as filas SQS.
"""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from app.saga.domain.value_objects import COMPENSATION_CONFIRMATIONS
from tests.conftest import outbox
from tests.saga_helpers import ORDER_INPUT, Participants, make_orchestrator

scenarios("features/fluxo_ordem_de_servico.feature")


@pytest.fixture
def ctx() -> dict:
    return {}


def _order(client: TestClient, headers: dict[str, str], ctx: dict) -> dict:
    return client.get(f"/service-orders/{ctx['order_id']}", headers=headers).json()


# ── Dado ─────────────────────────────────────────────────────────────────────


@given(parsers.parse('que o administrador abriu uma OS para o veículo "{plate}" com o problema "{problem}"'))
def open_order(client: TestClient, admin_headers: dict[str, str], ctx: dict, plate: str, problem: str) -> None:
    payload = {**ORDER_INPUT, "vehicle": {**ORDER_INPUT["vehicle"], "plate": plate}, "problem_description": problem}
    response = client.post("/service-orders", json=payload, headers=admin_headers)
    assert response.status_code == 201
    ctx["order_id"] = response.json()["id"]
    ctx["participants"] = Participants(make_orchestrator(), ctx["order_id"])


@given("que a OS chegou até o orçamento aguardando aprovação")
def until_quote(ctx: dict) -> None:
    p = ctx["participants"]
    p.emit("DiagnosticoEnfileirado")
    p.emit("DiagnosticoConcluido", notes="ok", services=[{"service_id": "s", "name": "Revisão", "quantity": 1, "unit_price": 200.0}], parts=[{"part_id": "p", "name": "Pastilha", "quantity": 2, "unit_price": 90.0}])
    p.emit("PecasReservadas", reservation_id="r-1")
    p.emit("OrcamentoGerado", quote_id="q-1", total=380.0)


@given("que a OS chegou até a cobrança criada")
def until_charge(ctx: dict) -> None:
    until_quote(ctx)
    ctx["participants"].emit("OrcamentoAprovado", quote_id="q-1", decided_by="cliente")
    ctx["participants"].emit("CobrancaCriada", charge_id="c-1", checkout_url="https://mp.test/c-1")


@given("que a OS chegou até a baixa das peças confirmada")
def until_withdrawal(ctx: dict) -> None:
    until_charge(ctx)
    ctx["participants"].emit("PagamentoConfirmado", charge_id="c-1")
    ctx["participants"].emit("BaixaConfirmada", reservation_id="r-1")


# ── Quando ───────────────────────────────────────────────────────────────────


@when("a Execução confirma que a OS entrou na fila de diagnóstico")
def diagnosis_enqueued(ctx: dict) -> None:
    ctx["participants"].emit("DiagnosticoEnfileirado")


@when("o mecânico inicia o diagnóstico")
def diagnosis_started(ctx: dict) -> None:
    ctx["participants"].emit("DiagnosticoIniciado")


@when(parsers.parse('o mecânico conclui o diagnóstico com {sq:d} "{service}" a {sp:f} e {pq:d} "{part}" a {pp:f}'))
def diagnosis_done(ctx: dict, sq: int, service: str, sp: float, pq: int, part: str, pp: float) -> None:
    ctx["participants"].emit(
        "DiagnosticoConcluido",
        notes="Óleo vencido",
        services=[{"service_id": "svc-1", "name": service, "quantity": sq, "unit_price": sp}],
        parts=[{"part_id": "part-1", "name": part, "quantity": pq, "unit_price": pp}],
    )


@when("o Estoque reserva as peças")
def parts_reserved(ctx: dict) -> None:
    ctx["participants"].emit("PecasReservadas", reservation_id="r-1")


@when("o Orçamento é gerado e enviado ao cliente")
def quote_generated(ctx: dict) -> None:
    ctx["participants"].emit("OrcamentoGerado", quote_id="q-1", total=330.0)


@when("o cliente aprova o orçamento")
def quote_approved(ctx: dict) -> None:
    ctx["participants"].emit("OrcamentoAprovado", quote_id="q-1", decided_by="cliente")


@when("o cliente recusa o orçamento")
def quote_rejected(ctx: dict) -> None:
    ctx["participants"].emit("OrcamentoRecusado", quote_id="q-1", decided_by="cliente")


@when("o Pagamento cria a cobrança no Mercado Pago")
def charge_created(ctx: dict) -> None:
    ctx["participants"].emit("CobrancaCriada", charge_id="c-1", checkout_url="https://mp.test/c-1")


@when("o pagamento é confirmado")
def payment_confirmed(ctx: dict) -> None:
    ctx["participants"].emit("PagamentoConfirmado", charge_id="c-1")


@when("o pagamento é recusado pelo provedor")
def payment_declined(ctx: dict) -> None:
    ctx["participants"].emit("PagamentoRecusado", charge_id="c-1", provider_status="expired")


@when("o Estoque confirma a baixa das peças")
def withdrawal_confirmed(ctx: dict) -> None:
    ctx["participants"].emit("BaixaConfirmada", reservation_id="r-1")


@when("a Execução confirma que a OS entrou na fila de reparo")
def repair_enqueued(ctx: dict) -> None:
    ctx["participants"].emit("ReparoEnfileirado")


@when("a Execução não aceita a OS na fila de reparo")
def repair_refused(ctx: dict) -> None:
    ctx["participants"].emit("EnfileiramentoFalhou", etapa="reparo", reason="status_aguardando_diagnostico")


@when("o mecânico inicia e conclui o reparo")
def repair_done(ctx: dict) -> None:
    ctx["participants"].emit("ReparoIniciado")
    ctx["participants"].emit("ExecucaoFinalizada", notes="Troca feita")


@when("o administrador entrega o veículo")
def deliver(client: TestClient, admin_headers: dict[str, str], ctx: dict) -> None:
    assert client.post(f"/service-orders/{ctx['order_id']}/deliver", headers=admin_headers).status_code == 200


# ── Então ────────────────────────────────────────────────────────────────────


@then(parsers.parse('o comando "{command}" é enviado para "{destination}"'))
def command_sent(command: str, destination: str) -> None:
    last = outbox()[-1]
    assert (last["type"], last["destination"]) == (command, destination)


@then(parsers.parse('a OS fica com status "{status}"'))
def order_status(client: TestClient, admin_headers: dict[str, str], ctx: dict, status: str) -> None:
    assert _order(client, admin_headers, ctx)["status"] == status


@then(parsers.parse("a OS tem total de {total:f}"))
def order_total(client: TestClient, admin_headers: dict[str, str], ctx: dict, total: float) -> None:
    assert _order(client, admin_headers, ctx)["quote_total"] == total


@then(parsers.parse('a saga fica no estado "{state}"'))
def saga_state(client: TestClient, admin_headers: dict[str, str], ctx: dict, state: str) -> None:
    assert client.get(f"/service-orders/{ctx['order_id']}/saga", headers=admin_headers).json()["state"] == state


@then(parsers.parse('o histórico da OS é "{history}"'))
def order_history(client: TestClient, admin_headers: dict[str, str], ctx: dict, history: str) -> None:
    assert [h["to_status"] for h in _order(client, admin_headers, ctx)["status_history"]] == history.split(", ")


@then(parsers.parse('as compensações são enviadas uma de cada vez, na ordem "{expected}"'))
def compensations_in_order(ctx: dict, expected: str) -> None:
    sent = []
    for _ in expected.split(", "):
        command = outbox()[-1]["type"]
        sent.append(command)
        # A próxima só sai depois da confirmação desta.
        ctx["participants"].emit(COMPENSATION_CONFIRMATIONS[command])
    assert sent == expected.split(", ")
