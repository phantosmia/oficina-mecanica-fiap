from abc import ABC, abstractmethod
from datetime import datetime
from types import TracebackType
from typing import Self

from app.shared.events import Envelope
from app.service_orders.domain.repository import IServiceOrderRepository
from app.saga.domain.saga import ServiceOrderSaga


class ISagaUnitOfWork(ABC):
    """Uma transação: saga, OS (via `orders`), comandos na outbox e mensagens
    processadas só são confirmados juntos, em `commit()`."""

    orders: IServiceOrderRepository

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None) -> None:
        self.rollback()

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def get(self, saga_id: str, for_update: bool = False) -> ServiceOrderSaga | None: ...

    @abstractmethod
    def get_by_order(self, order_id: int, for_update: bool = False) -> ServiceOrderSaga | None: ...

    @abstractmethod
    def save(self, saga: ServiceOrderSaga) -> None: ...

    @abstractmethod
    def list_due(self, now: datetime, limit: int = 50) -> list[str]:
        """IDs das sagas com prazo vencido."""
        ...

    @abstractmethod
    def mark_processed(self, message_id: str, message_type: str) -> bool:
        """False se o evento já tinha sido processado (reentrega)."""
        ...

    @abstractmethod
    def send(self, envelope: Envelope, destination: str) -> None:
        """Grava o comando na outbox, com a fila do participante de destino."""
        ...
