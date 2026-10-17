from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ClientRef:
    id: int


@dataclass
class VehicleRef:
    id: int


@dataclass
class OrderItem:
    """Serviço ou peça definido no diagnóstico, com o preço copiado do Catálogo."""

    kind: str  # "servico" ou "peca"
    item_id: str
    name: str
    quantity: int
    unit_price: float
    subtotal: float


@dataclass
class StatusChange:
    from_status: str | None
    to_status: str
    reason: str
    at: datetime


@dataclass
class AverageExecutionTimeData:
    finished_orders: int
    average_minutes: float


@dataclass
class ServiceOrderEntity:
    id: int
    client_id: int
    vehicle_id: int
    status: str
    problem_description: str
    diagnosis_notes: str | None
    labor_total: float
    parts_total: float
    quote_total: float
    client_name: str
    client_document_number: str
    client_email: str | None
    vehicle_plate: str
    vehicle_brand: str
    vehicle_model: str
    vehicle_year: int
    created_at: datetime
    updated_at: datetime | None
    quote_sent_at: datetime | None = None
    approved_at: datetime | None = None
    paid_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    delivered_at: datetime | None = None
    cancelled_at: datetime | None = None
    items: list[OrderItem] = field(default_factory=list)
    status_history: list[StatusChange] = field(default_factory=list)
