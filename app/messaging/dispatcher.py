"""Entrega ao orquestrador cada evento recebido em `os-saga-eventos` (fila que
assina os tópicos de Estoque, Execução, Orçamento e Pagamento, RFC-0007)."""

import json
import logging
from typing import Any

from app.shared.events import Envelope
from app.saga.application.orchestrator import SagaOrchestrator

logger = logging.getLogger(__name__)


def parse_body(body: str) -> Envelope:
    """Corpo da mensagem SQS → envelope (aceita também o embrulho do SNS
    quando `RawMessageDelivery` está desligado)."""
    data: dict[str, Any] = json.loads(body)
    if data.get("Type") == "Notification" and "Message" in data:
        data = json.loads(data["Message"])
    return Envelope(
        type=data["type"],
        payload=data.get("payload") or {},
        saga_id=data.get("saga_id"),
        order_id=data.get("order_id"),
        message_id=data["message_id"],
        occurred_at=data["occurred_at"],
    )


class Dispatcher:
    def __init__(self, orchestrator: SagaOrchestrator) -> None:
        self._orchestrator = orchestrator

    def handle(self, envelope: Envelope) -> bool:
        # Todo evento vai para a saga: a máquina de estados decide se ele
        # interessa ao estado atual (e registra quando ignora).
        self._orchestrator.handle_event(envelope)
        logger.info("evento processado type=%s message_id=%s saga_id=%s order_id=%s", envelope.type, envelope.message_id, envelope.saga_id, envelope.order_id)
        return True
