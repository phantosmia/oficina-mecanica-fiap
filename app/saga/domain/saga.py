"""Máquina de estados da saga da OS (ADR-0008 e ADR-0010; contrato em docs/saga.md).

Domínio puro: não conhece banco, fila nem FastAPI. Recebe o estado atual e
um evento (ou o vencimento de um prazo) e devolve uma `Decision` dizendo o
que fazer: o próximo estado (aplicado na própria saga), os comandos a enviar
e a mudança na OS. A camada de aplicação grava tudo isso numa transação só.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.service_orders.domain.value_objects import ServiceOrderStatus
from app.saga.domain.value_objects import (
    AWAITING_REPLY_STATES,
    COMPENSATION_CONFIRMATIONS,
    TERMINAL_STATES,
    TIMEOUT_COMPENSATIONS,
    SagaState,
    SagaTimeouts,
)


@dataclass(frozen=True)
class Command:
    type: str
    payload: dict[str, Any]


@dataclass
class OrderChange:
    """Mudança a aplicar na OS. `status=None` mantém o status atual."""

    reason: str
    status: ServiceOrderStatus | None = None
    # Campos da OS a atualizar (ex.: approved_at, diagnosis_notes, items, totais).
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    commands: list[Command] = field(default_factory=list)
    order_change: OrderChange | None = None
    notify_finished: bool = False
    ignored_reason: str | None = None

    @property
    def ignored(self) -> bool:
        return self.ignored_reason is not None


def _items(entries: list[dict[str, Any]], kind: str, id_key: str) -> list[dict[str, Any]]:
    return [
        {
            "kind": kind,
            "item_id": str(e[id_key]),
            "name": str(e["name"]),
            "quantity": int(e["quantity"]),
            "unit_price": float(e["unit_price"]),
            "subtotal": round(float(e["unit_price"]) * int(e["quantity"]), 2),
        }
        for e in entries
    ]


@dataclass
class ServiceOrderSaga:
    id: str
    order_id: int
    state: SagaState
    created_at: datetime
    data: dict[str, Any] = field(default_factory=dict)
    pending_compensations: list[str] = field(default_factory=list)
    final_status: ServiceOrderStatus | None = None
    failure_reason: str | None = None
    last_command: dict[str, Any] | None = None
    attempts: int = 0
    deadline_at: datetime | None = None
    updated_at: datetime | None = None

    # ── início ────────────────────────────────────────────────────────────────

    @classmethod
    def begin(
        cls,
        saga_id: str,
        order_id: int,
        customer: dict[str, Any],
        vehicle: dict[str, Any],
        problem_description: str,
        now: datetime,
        timeouts: SagaTimeouts,
    ) -> tuple["ServiceOrderSaga", Decision]:
        saga = cls(
            id=saga_id,
            order_id=order_id,
            state=SagaState.ENQUEUING_DIAGNOSIS,
            created_at=now,
            data={"customer": customer, "vehicle": vehicle, "problem_description": problem_description},
        )
        command = saga._send(
            "EnfileirarDiagnostico", {"problem_description": problem_description, "vehicle": vehicle}, now, timeouts
        )
        return saga, Decision(commands=[command])

    # ── eventos ───────────────────────────────────────────────────────────────

    def handle(self, event_type: str, payload: dict[str, Any], now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state in TERMINAL_STATES:
            return Decision(ignored_reason=f"saga já encerrada ({self.state.value})")
        if self.state == SagaState.COMPENSATING:
            return self._on_compensation_event(event_type, now, timeouts)
        handler = getattr(self, f"_on_{event_type}", None)
        if handler is None:
            return Decision(ignored_reason=f"evento {event_type} não esperado em {self.state.value}")
        self.updated_at = now
        return handler(payload, now, timeouts)

    # Execução: diagnóstico

    def _on_DiagnosticoEnfileirado(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state != SagaState.ENQUEUING_DIAGNOSIS:
            return self._unexpected("DiagnosticoEnfileirado")
        self._wait(SagaState.AWAITING_DIAGNOSIS, None)
        return Decision()

    def _on_DiagnosticoIniciado(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        # Aceito também antes do DiagnosticoEnfileirado (mensagens sem ordem garantida).
        if self.state not in (SagaState.ENQUEUING_DIAGNOSIS, SagaState.AWAITING_DIAGNOSIS):
            return self._unexpected("DiagnosticoIniciado")
        self._wait(SagaState.AWAITING_DIAGNOSIS, None)
        return Decision(order_change=OrderChange("diagnóstico iniciado pelo mecânico", ServiceOrderStatus.IN_DIAGNOSIS))

    def _on_DiagnosticoConcluido(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state not in (SagaState.ENQUEUING_DIAGNOSIS, SagaState.AWAITING_DIAGNOSIS):
            return self._unexpected("DiagnosticoConcluido")
        services = _items(payload.get("services", []), "servico", "service_id")
        parts = _items(payload.get("parts", []), "peca", "part_id")
        labor_total = round(sum(i["subtotal"] for i in services), 2)
        parts_total = round(sum(i["subtotal"] for i in parts), 2)
        self.data["diagnosis"] = {
            "notes": payload.get("notes", ""),
            "services": payload.get("services", []),
            "parts": payload.get("parts", []),
        }
        command = self._send(
            "ReservarPecas",
            {"items": [{"part_id": p["item_id"], "quantity": p["quantity"]} for p in parts]},
            now,
            timeouts,
            next_state=SagaState.RESERVING_PARTS,
        )
        change = OrderChange(
            "diagnóstico concluído",
            ServiceOrderStatus.IN_DIAGNOSIS,
            {
                "diagnosis_notes": payload.get("notes", ""),
                "items": services + parts,
                "labor_total": labor_total,
                "parts_total": parts_total,
                "quote_total": round(labor_total + parts_total, 2),
            },
        )
        return Decision(commands=[command], order_change=change)

    # Estoque: reserva

    def _on_PecasReservadas(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state != SagaState.RESERVING_PARTS:
            return self._unexpected("PecasReservadas")
        self.data["reservation_id"] = payload.get("reservation_id")
        diagnosis = self.data["diagnosis"]
        command = self._send(
            "GerarOrcamento",
            {
                "customer": self.data["customer"],
                "notes": diagnosis["notes"],
                "services": diagnosis["services"],
                "parts": diagnosis["parts"],
            },
            now,
            timeouts,
            next_state=SagaState.GENERATING_QUOTE,
        )
        return Decision(commands=[command])

    def _on_ReservaRecusada(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state != SagaState.RESERVING_PARTS:
            return self._unexpected("ReservaRecusada")
        return self._compensate([], ServiceOrderStatus.CANCELLED, f"reserva recusada: {payload.get('reason', '?')}", now, timeouts)

    # Orçamento

    def _on_OrcamentoGerado(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state != SagaState.GENERATING_QUOTE:
            return self._unexpected("OrcamentoGerado")
        self.data["quote"] = {"quote_id": payload.get("quote_id"), "total": payload.get("total")}
        self._wait(SagaState.AWAITING_APPROVAL, now + timeouts.approval)
        return Decision(
            order_change=OrderChange("orçamento enviado ao cliente", ServiceOrderStatus.WAITING_APPROVAL, {"quote_sent_at": now})
        )

    def _on_OrcamentoFalhou(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state != SagaState.GENERATING_QUOTE:
            return self._unexpected("OrcamentoFalhou")
        return self._compensate(["LiberarPecas"], ServiceOrderStatus.CANCELLED, f"falha ao gerar orçamento: {payload.get('reason', '?')}", now, timeouts)

    def _on_OrcamentoAprovado(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state != SagaState.AWAITING_APPROVAL:
            return self._unexpected("OrcamentoAprovado")
        diagnosis = self.data["diagnosis"]
        command = self._send(
            "CriarCobranca",
            {
                "quote_id": self.data.get("quote", {}).get("quote_id"),
                "customer": self.data["customer"],
                "services": diagnosis["services"],
                "parts": diagnosis["parts"],
            },
            now,
            timeouts,
            next_state=SagaState.CREATING_CHARGE,
        )
        by = payload.get("decided_by", "cliente")
        return Decision(
            commands=[command],
            order_change=OrderChange(f"orçamento aprovado ({by})", ServiceOrderStatus.WAITING_PAYMENT, {"approved_at": now}),
        )

    def _on_OrcamentoRecusado(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state != SagaState.AWAITING_APPROVAL:
            return self._unexpected("OrcamentoRecusado")
        by = payload.get("decided_by", "cliente")
        return self._compensate(["LiberarPecas"], ServiceOrderStatus.REJECTED, f"orçamento recusado ({by})", now, timeouts)

    # Pagamento

    def _on_CobrancaCriada(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state != SagaState.CREATING_CHARGE:
            return self._unexpected("CobrancaCriada")
        self.data["charge"] = {"charge_id": payload.get("charge_id"), "checkout_url": payload.get("checkout_url")}
        self._wait(SagaState.AWAITING_PAYMENT, now + timeouts.payment)
        return Decision()

    def _on_CobrancaFalhou(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state != SagaState.CREATING_CHARGE:
            return self._unexpected("CobrancaFalhou")
        return self._compensate(
            ["CancelarOrcamento", "LiberarPecas"], ServiceOrderStatus.CANCELLED, f"falha ao criar cobrança: {payload.get('reason', '?')}", now, timeouts
        )

    def _on_PagamentoConfirmado(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        # Aceito também antes do CobrancaCriada: o cliente pode pagar muito rápido.
        if self.state not in (SagaState.CREATING_CHARGE, SagaState.AWAITING_PAYMENT):
            return self._unexpected("PagamentoConfirmado")
        command = self._send("ConfirmarBaixa", {}, now, timeouts, next_state=SagaState.CONFIRMING_WITHDRAWAL)
        return Decision(commands=[command], order_change=OrderChange("pagamento confirmado", None, {"paid_at": now}))

    def _on_PagamentoRecusado(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state not in (SagaState.CREATING_CHARGE, SagaState.AWAITING_PAYMENT):
            return self._unexpected("PagamentoRecusado")
        return self._compensate(
            ["CancelarCobranca", "CancelarOrcamento", "LiberarPecas"],
            ServiceOrderStatus.CANCELLED,
            f"pagamento não concluído ({payload.get('provider_status', '?')})",
            now,
            timeouts,
        )

    # Estoque: baixa

    def _on_BaixaConfirmada(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state != SagaState.CONFIRMING_WITHDRAWAL:
            return self._unexpected("BaixaConfirmada")
        command = self._send("EnfileirarReparo", {}, now, timeouts, next_state=SagaState.ENQUEUING_REPAIR)
        return Decision(commands=[command])

    def _on_BaixaFalhou(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state != SagaState.CONFIRMING_WITHDRAWAL:
            return self._unexpected("BaixaFalhou")
        return self._compensate(
            ["EstornarPagamento", "CancelarOrcamento", "LiberarPecas"],
            ServiceOrderStatus.CANCELLED,
            f"falha na baixa do estoque: {payload.get('reason', '?')}",
            now,
            timeouts,
        )

    # Execução: reparo

    def _on_ReparoEnfileirado(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state != SagaState.ENQUEUING_REPAIR:
            return self._unexpected("ReparoEnfileirado")
        # Ponto sem volta (ADR-0010): daqui em diante não há compensação automática.
        self._wait(SagaState.IN_REPAIR, None)
        return Decision(order_change=OrderChange("OS na fila de reparo", ServiceOrderStatus.IN_PROGRESS))

    def _on_EnfileiramentoFalhou(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        reason = f"execução não aceitou a OS: {payload.get('reason', '?')}"
        if self.state == SagaState.ENQUEUING_DIAGNOSIS:
            return self._compensate([], ServiceOrderStatus.CANCELLED, reason, now, timeouts)
        if self.state == SagaState.ENQUEUING_REPAIR:
            return self._compensate(["EstornarPagamento", "CancelarOrcamento", "DevolverPecas"], ServiceOrderStatus.CANCELLED, reason, now, timeouts)
        return self._unexpected("EnfileiramentoFalhou")

    def _on_ReparoIniciado(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state not in (SagaState.ENQUEUING_REPAIR, SagaState.IN_REPAIR):
            return self._unexpected("ReparoIniciado")
        self._wait(SagaState.IN_REPAIR, None)
        return Decision(order_change=OrderChange("reparo iniciado pelo mecânico", ServiceOrderStatus.IN_PROGRESS, {"started_at": now}))

    def _on_ExecucaoFinalizada(self, payload: dict, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.state not in (SagaState.ENQUEUING_REPAIR, SagaState.IN_REPAIR):
            return self._unexpected("ExecucaoFinalizada")
        self._wait(SagaState.COMPLETED, None)
        return Decision(
            order_change=OrderChange("reparo concluído", ServiceOrderStatus.FINISHED, {"finished_at": now}),
            notify_finished=True,
        )

    # ── compensação ──────────────────────────────────────────────────────────

    def _compensate(self, compensations: list[str], final_status: ServiceOrderStatus, reason: str, now: datetime, timeouts: SagaTimeouts) -> Decision:
        """Desfaz os passos já concluídos, um de cada vez, na ordem dada. A
        próxima compensação só sai depois da confirmação da anterior."""
        self.final_status, self.failure_reason, self.updated_at = final_status, reason, now
        self.pending_compensations = list(compensations)
        if not self.pending_compensations:
            return self._finish_cancelled(now)
        command = self._send(self.pending_compensations[0], {}, now, timeouts, next_state=SagaState.COMPENSATING)
        return Decision(commands=[command])

    def _on_compensation_event(self, event_type: str, now: datetime, timeouts: SagaTimeouts) -> Decision:
        current = self.pending_compensations[0] if self.pending_compensations else None
        if current is None or COMPENSATION_CONFIRMATIONS[current] != event_type:
            # Evento atrasado do fluxo normal: a compensação em andamento já
            # cuida dele (ex.: o Pagamento estorna um pagamento que entrou agora).
            return Decision(ignored_reason=f"evento {event_type} durante compensação ({current} em andamento)")
        self.pending_compensations = self.pending_compensations[1:]
        self.updated_at = now
        if not self.pending_compensations:
            return self._finish_cancelled(now)
        return Decision(commands=[self._send(self.pending_compensations[0], {}, now, timeouts)])

    def _finish_cancelled(self, now: datetime) -> Decision:
        self._wait(SagaState.CANCELLED, None)
        status = self.final_status or ServiceOrderStatus.CANCELLED
        return Decision(order_change=OrderChange(self.failure_reason or "saga cancelada", status, {"cancelled_at": now}))

    # ── prazos ───────────────────────────────────────────────────────────────

    def on_deadline(self, now: datetime, timeouts: SagaTimeouts) -> Decision:
        if self.deadline_at is None or now < self.deadline_at or self.state in TERMINAL_STATES:
            return Decision(ignored_reason="prazo ainda não venceu")
        self.updated_at = now
        if self.state == SagaState.AWAITING_APPROVAL:
            return self._compensate(["CancelarOrcamento", "LiberarPecas"], ServiceOrderStatus.CANCELLED, "prazo de aprovação do orçamento expirado", now, timeouts)
        if self.state == SagaState.AWAITING_PAYMENT:
            return self._compensate(
                ["CancelarCobranca", "CancelarOrcamento", "LiberarPecas"], ServiceOrderStatus.CANCELLED, "prazo de pagamento expirado", now, timeouts
            )
        if self.state in AWAITING_REPLY_STATES and self.last_command:
            if self.attempts < timeouts.max_attempts:
                self.attempts += 1
                self.deadline_at = now + timeouts.reply
                return Decision(commands=[Command(self.last_command["type"], self.last_command["payload"])])
            if self.state == SagaState.COMPENSATING:
                # Compensação não pode ser abandonada: fica parada, visível, à
                # espera de intervenção (POST /service-orders/{id}/saga/retry).
                self.deadline_at = None
                self.failure_reason = f"{self.failure_reason}; {self.last_command['type']} sem resposta, aguardando intervenção"
                return Decision(ignored_reason="compensação sem resposta após todas as tentativas")
            failed_step = self.state
            return self._compensate(
                TIMEOUT_COMPENSATIONS[failed_step], ServiceOrderStatus.CANCELLED, f"sem resposta em {failed_step.value}", now, timeouts
            )
        return Decision(ignored_reason=f"nada a fazer no prazo em {self.state.value}")

    def retry(self, now: datetime, timeouts: SagaTimeouts) -> Decision:
        """Reenvio manual do último comando (admin), para compensação parada."""
        if self.state not in AWAITING_REPLY_STATES or not self.last_command:
            return Decision(ignored_reason=f"nada a reenviar em {self.state.value}")
        self.attempts, self.deadline_at, self.updated_at = 1, now + timeouts.reply, now
        return Decision(commands=[Command(self.last_command["type"], self.last_command["payload"])])

    # ── auxiliares ───────────────────────────────────────────────────────────

    def _send(self, command_type: str, payload: dict, now: datetime, timeouts: SagaTimeouts, next_state: SagaState | None = None) -> Command:
        if next_state is not None:
            self.state = next_state
        self.last_command = {"type": command_type, "payload": payload}
        self.attempts = 1
        self.deadline_at = now + timeouts.reply
        return Command(command_type, payload)

    def _wait(self, state: SagaState, deadline: datetime | None) -> None:
        self.state, self.deadline_at, self.last_command, self.attempts = state, deadline, None, 0

    def _unexpected(self, event_type: str) -> Decision:
        return Decision(ignored_reason=f"evento {event_type} não esperado em {self.state.value}")
