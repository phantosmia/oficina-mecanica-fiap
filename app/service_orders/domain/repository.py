from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.service_orders.domain.entities import AverageExecutionTimeData, ClientRef, ServiceOrderEntity, VehicleRef
from app.service_orders.domain.value_objects import ServiceOrderStatus


class IServiceOrderRepository(ABC):
    """Nada aqui faz commit sozinho: quem decide a transação é o caso de uso
    (`commit()`), porque abrir a OS e iniciar a saga precisam ir juntos."""

    @abstractmethod
    def upsert_client(self, name: str, document_type: str, document_number: str, email: str | None, phone: str | None) -> ClientRef: ...

    @abstractmethod
    def upsert_vehicle(self, client_id: int, brand: str, model: str, year: int, plate: str) -> VehicleRef: ...

    @abstractmethod
    def create_order(self, client_id: int, vehicle_id: int, problem_description: str, now: datetime) -> ServiceOrderEntity: ...

    @abstractmethod
    def list_active_orders(self) -> list[ServiceOrderEntity]:
        """OS com trabalho pendente, por prioridade de status e depois as mais antigas."""
        ...

    @abstractmethod
    def get_order(self, order_id: int) -> ServiceOrderEntity | None: ...

    @abstractmethod
    def apply_change(
        self, order_id: int, status: ServiceOrderStatus | None, reason: str, fields: dict[str, Any], now: datetime
    ) -> tuple[str, ServiceOrderEntity]:
        """Aplica uma mudança na OS (status, campos, itens) e registra no
        histórico se o status mudou. Retorna (status anterior, OS atualizada)."""
        ...

    @abstractmethod
    def get_tracking(self, order_id: int, document_number: str) -> ServiceOrderEntity | None: ...

    @abstractmethod
    def get_average_execution_time(self) -> AverageExecutionTimeData: ...

    @abstractmethod
    def commit(self) -> None: ...


class ISagaStarter(ABC):
    """Porta para o orquestrador (app/saga): inicia a saga de uma OS recém-aberta
    **na mesma transação** da abertura."""

    @abstractmethod
    def start(self, order: ServiceOrderEntity) -> None: ...
