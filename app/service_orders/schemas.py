from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.shared.validators import validate_document, validate_plate
from app.service_orders.domain.value_objects import ServiceOrderStatus


class ServiceOrderClientInput(BaseModel):
    name: str
    document_number: str
    email: EmailStr | None = None
    phone: str | None = None

    @field_validator("document_number")
    @classmethod
    def validate_document_number(cls, value: str) -> str:
        return validate_document(value)


class ServiceOrderVehicleInput(BaseModel):
    plate: str
    brand: str
    model: str
    year: int = Field(ge=1900, le=2100)

    @field_validator("plate")
    @classmethod
    def validate_plate_number(cls, value: str) -> str:
        return validate_plate(value)


class ServiceOrderCreate(BaseModel):
    """Abertura da OS (ADR-0010): só cliente, veículo e o problema relatado.
    Os serviços e peças são definidos depois, pelo mecânico, no diagnóstico."""

    client: ServiceOrderClientInput
    vehicle: ServiceOrderVehicleInput
    problem_description: str = Field(min_length=3)


class ServiceOrderItemRead(BaseModel):
    kind: str = Field(description="servico ou peca")
    item_id: str
    name: str
    quantity: int
    unit_price: float
    subtotal: float


class StatusChangeRead(BaseModel):
    from_status: str | None
    to_status: str
    reason: str
    at: datetime


class ServiceOrderSummary(BaseModel):
    id: int
    status: ServiceOrderStatus
    client_name: str
    client_document_number: str
    vehicle_plate: str
    vehicle_model: str
    quote_total: float
    created_at: datetime
    updated_at: datetime | None = None


class ServiceOrderRead(ServiceOrderSummary):
    client_id: int
    vehicle_id: int
    problem_description: str
    diagnosis_notes: str | None = None
    labor_total: float
    parts_total: float
    quote_sent_at: datetime | None = None
    approved_at: datetime | None = None
    paid_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    delivered_at: datetime | None = None
    cancelled_at: datetime | None = None
    items: list[ServiceOrderItemRead]
    status_history: list[StatusChangeRead]


class ServiceOrderTracking(BaseModel):
    id: int
    status: ServiceOrderStatus
    client_name: str
    vehicle_plate: str
    quote_total: float
    created_at: datetime
    items: list[ServiceOrderItemRead]
    status_history: list[StatusChangeRead]


class AverageExecutionTimeRead(BaseModel):
    finished_orders: int
    average_minutes: float


class SagaRead(BaseModel):
    """Estado da saga da OS (para acompanhar o fluxo distribuído)."""

    saga_id: str
    order_id: int
    state: str
    pending_compensations: list[str]
    final_status: str | None
    failure_reason: str | None
    waiting_for: str | None = Field(description="Último comando enviado, se a saga espera a resposta dele")
    attempts: int
    deadline_at: datetime | None
    data: dict
    created_at: datetime
    updated_at: datetime | None
