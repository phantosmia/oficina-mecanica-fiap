from abc import ABC, abstractmethod

from app.service_orders.domain.entities import (
    AverageExecutionTimeData,
    CatalogServiceRef,
    ClientRef,
    PartItemInput,
    PartRef,
    ServiceItemInput,
    ServiceOrderEntity,
    VehicleRef,
)


class IServiceOrderRepository(ABC):
    # ── cross-domain lookups needed by CreateServiceOrderUseCase ──────────────

    @abstractmethod
    def upsert_client(
        self,
        name: str,
        document_type: str,
        document_number: str,
        email: str | None,
        phone: str | None,
    ) -> ClientRef: ...

    @abstractmethod
    def upsert_vehicle(
        self,
        client_id: int,
        brand: str,
        model: str,
        year: int,
        plate: str,
    ) -> VehicleRef: ...

    @abstractmethod
    def find_active_catalog_service(self, service_id: int) -> CatalogServiceRef | None: ...

    @abstractmethod
    def find_part(self, part_id: int) -> PartRef | None: ...

    # ── order CRUD ────────────────────────────────────────────────────────────

    @abstractmethod
    def create_order(
        self,
        client_id: int,
        vehicle_id: int,
        problem_description: str,
        service_items: list[ServiceItemInput],
        part_items: list[PartItemInput],
        labor_total: float,
        parts_total: float,
        quote_total: float,
    ) -> ServiceOrderEntity: ...

    @abstractmethod
    def list_orders(self) -> list[ServiceOrderEntity]: ...

    @abstractmethod
    def get_order(self, order_id: int) -> ServiceOrderEntity | None: ...

    @abstractmethod
    def update_order_fields(self, order_id: int, fields: dict[str, object]) -> ServiceOrderEntity | None: ...

    # ── atomic approval (stock decrement + status change) ────────────────────

    @abstractmethod
    def execute_approval(self, order_id: int) -> ServiceOrderEntity | None: ...

    # ── public tracking and metrics ───────────────────────────────────────────

    @abstractmethod
    def get_tracking(self, order_id: int, document_number: str) -> ServiceOrderEntity | None: ...

    @abstractmethod
    def get_average_execution_time(self) -> AverageExecutionTimeData: ...
