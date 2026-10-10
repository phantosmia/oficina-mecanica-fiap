"""Testes unitários da máquina de estados da saga (domínio puro, sem banco).
Cada caso corresponde a uma linha das tabelas de docs/saga.md."""

from datetime import UTC, datetime, timedelta

import pytest

from app.service_orders.domain.value_objects import ServiceOrderStatus
from app.saga.domain.saga import ServiceOrderSaga
from app.saga.domain.value_objects import SagaState
from tests.saga_helpers import DIAGNOSIS, TIMEOUTS

T0 = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
CUSTOMER = {"name": "Maria", "email": "maria@example.com"}
VEHICLE = {"plate": "BRA2E19", "brand": "VW", "model": "Gol", "year": 2018}


def new_saga() -> ServiceOrderSaga:
    saga, _ = ServiceOrderSaga.begin("s-1", 42, CUSTOMER, VEHICLE, "Barulho", T0, TIMEOUTS)
    return saga


def run(saga: ServiceOrderSaga, *events: tuple[str, dict]) -> list:
    decisions = [saga.handle(event_type, payload, T0, TIMEOUTS) for event_type, payload in events]
    return decisions


HAPPY_PATH = [
    ("DiagnosticoEnfileirado", {}),
    ("DiagnosticoIniciado", {}),
    ("DiagnosticoConcluido", DIAGNOSIS),
    ("PecasReservadas", {"reservation_id": "r-1"}),
    ("OrcamentoGerado", {"quote_id": "q-1", "total": 355.5}),
    ("OrcamentoAprovado", {"quote_id": "q-1", "decided_by": "cliente"}),
    ("CobrancaCriada", {"charge_id": "c-1", "checkout_url": "https://mp/x"}),
    ("PagamentoConfirmado", {"charge_id": "c-1"}),
    ("BaixaConfirmada", {}),
    ("ReparoEnfileirado", {}),
    ("ReparoIniciado", {}),
    ("ExecucaoFinalizada", {"notes": "ok"}),
]


def advance(saga: ServiceOrderSaga, until: str) -> None:
    for event_type, payload in HAPPY_PATH:
        assert not saga.handle(event_type, payload, T0, TIMEOUTS).ignored
        if event_type == until:
            return


def test_begin_sends_diagnosis_command() -> None:
    saga, decision = ServiceOrderSaga.begin("s-1", 42, CUSTOMER, VEHICLE, "Barulho", T0, TIMEOUTS)
    assert saga.state == SagaState.ENQUEUING_DIAGNOSIS
    assert [(c.type, c.payload) for c in decision.commands] == [("EnfileirarDiagnostico", {"problem_description": "Barulho", "vehicle": VEHICLE})]
    assert saga.deadline_at == T0 + TIMEOUTS.reply


def test_happy_path_commands_states_and_statuses() -> None:
    saga = new_saga()
    trail = []
    for event_type, payload in HAPPY_PATH:
        decision = saga.handle(event_type, payload, T0, TIMEOUTS)
        status = decision.order_change.status.value if decision.order_change and decision.order_change.status else None
        trail.append((event_type, saga.state.value, [c.type for c in decision.commands], status))

    assert trail == [
        ("DiagnosticoEnfileirado", "AGUARDANDO_DIAGNOSTICO", [], None),
        ("DiagnosticoIniciado", "AGUARDANDO_DIAGNOSTICO", [], "em_diagnostico"),
        ("DiagnosticoConcluido", "RESERVANDO_PECAS", ["ReservarPecas"], "em_diagnostico"),
        ("PecasReservadas", "GERANDO_ORCAMENTO", ["GerarOrcamento"], None),
        ("OrcamentoGerado", "AGUARDANDO_APROVACAO", [], "aguardando_aprovacao"),
        ("OrcamentoAprovado", "GERANDO_COBRANCA", ["CriarCobranca"], "aguardando_pagamento"),
        ("CobrancaCriada", "AGUARDANDO_PAGAMENTO", [], None),
        ("PagamentoConfirmado", "CONFIRMANDO_BAIXA", ["ConfirmarBaixa"], None),
        ("BaixaConfirmada", "ENFILEIRANDO_REPARO", ["EnfileirarReparo"], None),
        ("ReparoEnfileirado", "EM_REPARO", [], "em_execucao"),
        ("ReparoIniciado", "EM_REPARO", [], "em_execucao"),
        ("ExecucaoFinalizada", "CONCLUIDA", [], "finalizada"),
    ]
    assert saga.deadline_at is None


def test_command_payloads_carry_what_each_participant_needs() -> None:
    saga = new_saga()
    reserve = run(saga, ("DiagnosticoEnfileirado", {}), ("DiagnosticoConcluido", DIAGNOSIS))[-1]
    assert reserve.commands[0].payload == {"items": [{"part_id": "part-oleo", "quantity": 4}, {"part_id": "part-filtro", "quantity": 1}]}
    change = reserve.order_change.fields
    assert (change["labor_total"], change["parts_total"], change["quote_total"]) == (150.0, 205.5, 355.5)
    assert [i["kind"] for i in change["items"]] == ["servico", "peca", "peca"]

    quote = saga.handle("PecasReservadas", {"reservation_id": "r-1"}, T0, TIMEOUTS).commands[0]
    assert quote.payload == {"customer": CUSTOMER, "notes": DIAGNOSIS["notes"], "services": DIAGNOSIS["services"], "parts": DIAGNOSIS["parts"]}

    run(saga, ("OrcamentoGerado", {"quote_id": "q-1"}))
    charge = saga.handle("OrcamentoAprovado", {}, T0, TIMEOUTS).commands[0]
    assert charge.payload == {"quote_id": "q-1", "customer": CUSTOMER, "services": DIAGNOSIS["services"], "parts": DIAGNOSIS["parts"]}


def test_out_of_order_diagnosis_events_are_accepted() -> None:
    saga = new_saga()
    # DiagnosticoIniciado e DiagnosticoConcluido antes do DiagnosticoEnfileirado.
    assert not saga.handle("DiagnosticoIniciado", {}, T0, TIMEOUTS).ignored
    assert saga.handle("DiagnosticoConcluido", DIAGNOSIS, T0, TIMEOUTS).commands[0].type == "ReservarPecas"
    assert saga.handle("DiagnosticoEnfileirado", {}, T0, TIMEOUTS).ignored


def test_payment_before_charge_created_is_accepted() -> None:
    saga = new_saga()
    advance(saga, "OrcamentoAprovado")
    assert saga.handle("PagamentoConfirmado", {}, T0, TIMEOUTS).commands[0].type == "ConfirmarBaixa"


def test_unexpected_and_late_events_are_ignored() -> None:
    saga = new_saga()
    assert saga.handle("BaixaConfirmada", {}, T0, TIMEOUTS).ignored
    assert saga.handle("EventoInventado", {}, T0, TIMEOUTS).ignored
    assert saga.state == SagaState.ENQUEUING_DIAGNOSIS
    advance(saga, "ExecucaoFinalizada")
    assert saga.handle("ReparoIniciado", {}, T0, TIMEOUTS).ignored_reason == "saga já encerrada (CONCLUIDA)"


# ── Falhas e compensações (docs/saga.md, "Ordem das compensações por ponto de falha") ──

FAILURES = [
    ("DiagnosticoEnfileirado", "EnfileiramentoFalhou", [], ServiceOrderStatus.CANCELLED),
    ("DiagnosticoConcluido", "ReservaRecusada", [], ServiceOrderStatus.CANCELLED),
    ("PecasReservadas", "OrcamentoFalhou", ["LiberarPecas"], ServiceOrderStatus.CANCELLED),
    ("OrcamentoGerado", "OrcamentoRecusado", ["LiberarPecas"], ServiceOrderStatus.REJECTED),
    ("OrcamentoAprovado", "CobrancaFalhou", ["CancelarOrcamento", "LiberarPecas"], ServiceOrderStatus.CANCELLED),
    ("CobrancaCriada", "PagamentoRecusado", ["CancelarCobranca", "CancelarOrcamento", "LiberarPecas"], ServiceOrderStatus.CANCELLED),
    ("PagamentoConfirmado", "BaixaFalhou", ["EstornarPagamento", "CancelarOrcamento", "LiberarPecas"], ServiceOrderStatus.CANCELLED),
    ("BaixaConfirmada", "EnfileiramentoFalhou", ["EstornarPagamento", "CancelarOrcamento", "DevolverPecas"], ServiceOrderStatus.CANCELLED),
]
CONFIRMATIONS = {
    "LiberarPecas": "PecasLiberadas",
    "DevolverPecas": "PecasDevolvidas",
    "CancelarOrcamento": "OrcamentoCancelado",
    "CancelarCobranca": "CobrancaCancelada",
    "EstornarPagamento": "PagamentoEstornado",
}


@pytest.mark.parametrize(("after", "failure", "compensations", "final_status"), FAILURES)
def test_compensations_run_one_at_a_time_in_order(after: str, failure: str, compensations: list[str], final_status: ServiceOrderStatus) -> None:
    saga = new_saga()
    advance(saga, after)
    if failure == "EnfileiramentoFalhou" and after == "DiagnosticoEnfileirado":
        saga = new_saga()  # falha no próprio enfileiramento do diagnóstico

    decision = saga.handle(failure, {"reason": "teste"}, T0, TIMEOUTS)
    sent = [c.type for c in decision.commands]
    while saga.state == SagaState.COMPENSATING:
        assert len(decision.commands) == 1  # uma compensação por vez
        decision = saga.handle(CONFIRMATIONS[decision.commands[0].type], {}, T0, TIMEOUTS)
        sent += [c.type for c in decision.commands]

    assert sent == compensations
    assert saga.state == SagaState.CANCELLED
    assert (decision.order_change.status, "cancelled_at" in decision.order_change.fields) == (final_status, True)


def test_wrong_confirmation_does_not_advance_compensation() -> None:
    saga = new_saga()
    advance(saga, "CobrancaCriada")
    saga.handle("PagamentoRecusado", {}, T0, TIMEOUTS)  # CancelarCobranca em andamento
    assert saga.handle("PecasLiberadas", {}, T0, TIMEOUTS).ignored
    assert saga.handle("PagamentoConfirmado", {}, T0, TIMEOUTS).ignored  # o Pagamento cuida (estorna)
    assert saga.pending_compensations == ["CancelarCobranca", "CancelarOrcamento", "LiberarPecas"]


# ── Prazos ───────────────────────────────────────────────────────────────────


def test_participant_silence_resends_then_compensates() -> None:
    saga = new_saga()
    advance(saga, "PecasReservadas")  # GERANDO_ORCAMENTO: espera o Orçamento
    t = T0
    for attempt in (2, 3):
        t += TIMEOUTS.reply
        decision = saga.on_deadline(t, TIMEOUTS)
        assert ([c.type for c in decision.commands], saga.attempts) == (["GerarOrcamento"], attempt)

    t += TIMEOUTS.reply
    decision = saga.on_deadline(t, TIMEOUTS)
    assert saga.state == SagaState.COMPENSATING
    assert [c.type for c in decision.commands] == ["CancelarOrcamento"]
    assert saga.pending_compensations == ["CancelarOrcamento", "LiberarPecas"]
    assert "sem resposta em GERANDO_ORCAMENTO" in saga.failure_reason


def test_deadline_not_reached_does_nothing() -> None:
    saga = new_saga()
    assert saga.on_deadline(T0 + timedelta(seconds=1), TIMEOUTS).ignored


@pytest.mark.parametrize(
    ("after", "wait", "compensations"),
    [
        ("OrcamentoGerado", TIMEOUTS.approval, ["CancelarOrcamento", "LiberarPecas"]),
        ("CobrancaCriada", TIMEOUTS.payment, ["CancelarCobranca", "CancelarOrcamento", "LiberarPecas"]),
    ],
)
def test_customer_deadlines_compensate(after: str, wait: timedelta, compensations: list[str]) -> None:
    saga = new_saga()
    advance(saga, after)
    saga.on_deadline(T0 + wait, TIMEOUTS)
    assert saga.pending_compensations == compensations


def test_stuck_compensation_waits_for_manual_retry() -> None:
    saga = new_saga()
    advance(saga, "OrcamentoGerado")
    saga.handle("OrcamentoRecusado", {}, T0, TIMEOUTS)  # LiberarPecas
    t = T0
    for _ in range(3):
        t += TIMEOUTS.reply
        saga.on_deadline(t, TIMEOUTS)
    assert saga.state == SagaState.COMPENSATING
    assert saga.deadline_at is None
    assert "aguardando intervenção" in saga.failure_reason

    retry = saga.retry(t, TIMEOUTS)
    assert [c.type for c in retry.commands] == ["LiberarPecas"] and saga.deadline_at is not None
    assert saga.handle("PecasLiberadas", {}, t, TIMEOUTS).order_change.status == ServiceOrderStatus.REJECTED


def test_retry_with_nothing_to_resend() -> None:
    saga = new_saga()
    advance(saga, "OrcamentoGerado")
    assert saga.retry(T0, TIMEOUTS).ignored
