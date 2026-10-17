"""Relay da outbox (RFC-0007): envia para a fila SQS de cada participante os
comandos que o orquestrador gravou em `outbox_messages`, na mesma transação
do avanço da saga.

Entrega *at-least-once*: se o processo cair entre enviar e marcar como
enviado, o comando sai de novo; os participantes descartam repetições pelo
`message_id`.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any, Protocol

import boto3
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.shared.models import OutboxMessage
from app.shared.settings import settings

logger = logging.getLogger(__name__)


class CommandSender(Protocol):
    def send(self, destination: str, envelope: dict[str, Any], trace_headers: dict[str, str]) -> None: ...


def message_attributes(envelope: dict[str, Any], trace_headers: dict[str, str]) -> dict[str, dict[str, str]]:
    """Mesmos `MessageAttributes` dos participantes (docs/saga.md, "Envelope")."""
    attributes = {"type": envelope["type"], "correlation_id": envelope.get("saga_id") or envelope["message_id"]}
    if envelope.get("saga_id"):
        attributes["saga_id"] = envelope["saga_id"]
    if envelope.get("order_id") is not None:
        attributes["order_id"] = str(envelope["order_id"])
    attributes.update(trace_headers)
    return {name: {"DataType": "String", "StringValue": value} for name, value in attributes.items()}


class SqsCommandSender:
    def __init__(self, queue_urls: dict[str, str]) -> None:
        self._queue_urls = queue_urls
        self._client = boto3.client("sqs", region_name=settings.aws_region)

    def send(self, destination: str, envelope: dict[str, Any], trace_headers: dict[str, str]) -> None:
        queue_url = self._queue_urls.get(destination)
        if not queue_url:
            raise RuntimeError(f"Fila de comandos não configurada para o participante '{destination}'.")
        self._client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(envelope, ensure_ascii=False),
            MessageAttributes=message_attributes(envelope, trace_headers),
        )


class OutboxRelay:
    def __init__(self, session_factory: sessionmaker[Session], sender: CommandSender, batch_size: int = 50) -> None:
        self._session_factory = session_factory
        self._sender = sender
        self._batch_size = batch_size

    def run_once(self) -> int:
        """Envia um lote de comandos pendentes, em ordem de gravação. Retorna quantos enviou."""
        with self._session_factory() as session:
            pending = session.scalars(
                select(OutboxMessage)
                .where(OutboxMessage.published_at.is_(None))
                .order_by(OutboxMessage.id)
                .limit(self._batch_size)
                .with_for_update(skip_locked=True)
            ).all()
            for message in pending:
                self._sender.send(message.destination, message.envelope, dict(message.trace_headers or {}))
                message.published_at = datetime.now(UTC)
                session.flush()
                logger.info("comando enviado type=%s destino=%s message_id=%s", message.message_type, message.destination, message.message_id)
            session.commit()
            return len(pending)
