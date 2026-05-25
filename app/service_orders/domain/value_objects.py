from enum import StrEnum

from app.shared.exceptions import InvalidTransitionError


class ServiceOrderStatus(StrEnum):
    RECEIVED = "recebida"
    IN_DIAGNOSIS = "em_diagnostico"
    WAITING_APPROVAL = "aguardando_aprovacao"
    IN_PROGRESS = "em_execucao"
    FINISHED = "finalizada"
    DELIVERED = "entregue"
    REJECTED = "recusada"


ALLOWED_TRANSITIONS: dict[ServiceOrderStatus, set[ServiceOrderStatus]] = {
    ServiceOrderStatus.RECEIVED: {ServiceOrderStatus.IN_DIAGNOSIS, ServiceOrderStatus.WAITING_APPROVAL},
    ServiceOrderStatus.IN_DIAGNOSIS: {ServiceOrderStatus.WAITING_APPROVAL},
    ServiceOrderStatus.WAITING_APPROVAL: {ServiceOrderStatus.IN_PROGRESS, ServiceOrderStatus.REJECTED},
    ServiceOrderStatus.IN_PROGRESS: {ServiceOrderStatus.FINISHED},
    ServiceOrderStatus.FINISHED: {ServiceOrderStatus.DELIVERED},
    ServiceOrderStatus.DELIVERED: set(),
    ServiceOrderStatus.REJECTED: set(),
}


def ensure_transition(current: ServiceOrderStatus, target: ServiceOrderStatus) -> None:
    """Raises InvalidTransitionError if the status transition is not allowed."""
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(
            f"Não é possível alterar o status de {current.value} para {target.value}."
        )
