from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ClientRef:
    id: int


@dataclass
class VehicleRef:
    id: int


@dataclass
class CatalogServiceRef:
    id: int
    base_price: float


@dataclass
class PartRef:
    id: int
    name: str
    unit_price: float
    stock_quantity: int


@dataclass
class ServiceItemInput:
    service_id: int
    quantity: int
    unit_price: float
    subtotal: float


@dataclass
class PartItemInput:
    part_id: int
    quantity: int
    unit_price: float
    subtotal: float


@dataclass
class ServiceItemEntity:
    service_id: int
    name: str
    quantity: int
    unit_price: float
    subtotal: float


@dataclass
class PartItemEntity:
    part_id: int
    name: str
    sku: str
    quantity: int
    unit_price: float
    subtotal: float


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
    vehicle_model: str
    created_at: datetime
    updated_at: datetime | None
    quote_sent_at: datetime | None
    approved_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    delivered_at: datetime | None
    service_items: list[ServiceItemEntity] = field(default_factory=list)
    part_items: list[PartItemEntity] = field(default_factory=list)
