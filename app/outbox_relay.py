"""Processo que envia os comandos da outbox às filas dos participantes
(`python -m app.outbox_relay`). Deployment próprio com 1 réplica."""

import logging
import time

from app.shared.database import get_session_factory
from app.shared.logging_config import configure_logging
from app.shared.outbox import OutboxRelay, SqsCommandSender
from app.shared.settings import settings

logger = logging.getLogger("app.outbox_relay")


def main() -> None:  # pragma: no cover - laço infinito; a lógica testada fica em OutboxRelay
    configure_logging(settings.log_level)
    relay = OutboxRelay(get_session_factory(), SqsCommandSender(settings.command_queue_urls))
    logger.info("relay da outbox iniciado destinos=%s", sorted(k for k, v in settings.command_queue_urls.items() if v))
    while True:
        try:
            if relay.run_once() == 0:
                time.sleep(settings.outbox_poll_interval_seconds)
        except Exception:
            logger.exception("falha ao enviar comandos da outbox; tentando de novo")
            time.sleep(settings.outbox_poll_interval_seconds)


if __name__ == "__main__":  # pragma: no cover
    main()
