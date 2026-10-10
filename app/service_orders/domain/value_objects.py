from enum import StrEnum

from app.shared.exceptions import InvalidTransitionError


class ServiceOrderStatus(StrEnum):
    """Status da OS visto pelo cliente (docs/saga.md, "Estados da saga e
    status da OS"). Quem muda o status é a saga, a partir dos eventos dos
    participantes; a única transição manual é a entrega."""

    RECEIVED = "recebida"
    IN_DIAGNOSIS = "em_diagnostico"
    WAITING_APPROVAL = "aguardando_aprovacao"
    WAITING_PAYMENT = "aguardando_pagamento"
    IN_PROGRESS = "em_execucao"
    FINISHED = "finalizada"
    DELIVERED = "entregue"
    REJECTED = "recusada"
    CANCELLED = "cancelada"


# Status sem trabalho pendente: saem da listagem padrão.
INACTIVE_STATUSES = {ServiceOrderStatus.FINISHED, ServiceOrderStatus.DELIVERED, ServiceOrderStatus.REJECTED, ServiceOrderStatus.CANCELLED}


def ensure_can_deliver(current: ServiceOrderStatus) -> None:
    if current != ServiceOrderStatus.FINISHED:
        raise InvalidTransitionError(f"Só é possível entregar uma OS finalizada (status atual: {current.value}).")
