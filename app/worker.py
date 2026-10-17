"""Processo do orquestrador que não atende HTTP (`python -m app.worker`):

- consome os eventos dos participantes (fila `os-saga-eventos`);
- verifica periodicamente os prazos da saga (resposta de participante,
  aprovação do orçamento, pagamento), reenviando comandos ou compensando.
"""

import logging
import threading
import time

from app.messaging.dispatcher import Dispatcher
from app.messaging.sqs_consumer import SqsConsumer
from app.shared.logging_config import configure_logging
from app.shared.settings import settings
from app.saga.application.orchestrator import SagaOrchestrator
from app.saga.wiring import build_orchestrator

logger = logging.getLogger("app.worker")


def _check_deadlines_forever(orchestrator: SagaOrchestrator) -> None:  # pragma: no cover
    while True:
        try:
            acted = orchestrator.process_deadlines()
            if acted:
                logger.info("prazos: %s sagas agiram", acted)
        except Exception:
            logger.exception("falha ao verificar prazos; tentando de novo")
        time.sleep(settings.deadline_check_interval_seconds)


def main() -> None:  # pragma: no cover - laços infinitos; a lógica testada fica no orquestrador
    configure_logging(settings.log_level)
    orchestrator = build_orchestrator()
    threading.Thread(target=_check_deadlines_forever, args=(orchestrator,), name="prazos", daemon=True).start()
    consumer = SqsConsumer([settings.saga_events_queue_url], Dispatcher(orchestrator), settings.worker_wait_seconds)
    logger.info("worker do orquestrador iniciado fila=%s", settings.saga_events_queue_url)
    while True:
        try:
            consumer.poll_queue(settings.saga_events_queue_url)
        except Exception:
            logger.exception("falha ao ler a fila; tentando de novo")


if __name__ == "__main__":  # pragma: no cover
    main()
