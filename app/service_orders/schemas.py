from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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


class ServiceOrderServiceItemCreate(BaseModel):
    service_id: int
    quantity: int = Field(default=1, ge=1)


class ServiceOrderPartItemCreate(BaseModel):
    part_id: int
    quantity: int = Field(default=1, ge=1)


class ServiceOrderCreate(BaseModel):
    client: ServiceOrderClientInput
    vehicle: ServiceOrderVehicleInput
    problem_description: str
    requested_services: list[ServiceOrderServiceItemCreate] = Field(min_length=1)
    requested_parts: list[ServiceOrderPartItemCreate] = Field(default_factory=list)


class ServiceOrderDiagnosisUpdate(BaseModel):
    diagnosis_notes: str = Field(min_length=3)


class ServiceOrderQuoteSend(BaseModel):
    diagnosis_notes: str | None = None


class ServiceOrderServiceItemRead(BaseModel):
    service_id: int
    name: str
    quantity: int
    unit_price: float
    subtotal: float


class ServiceOrderPartItemRead(BaseModel):
    part_id: int
    name: str
    sku: str
    quantity: int
    unit_price: float
    subtotal: float


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
    started_at: datetime | None = None
    finished_at: datetime | None = None
    delivered_at: datetime | None = None
    services: list[ServiceOrderServiceItemRead]
    parts: list[ServiceOrderPartItemRead]

    model_config = ConfigDict(from_attributes=True)


class ServiceOrderTracking(BaseModel):
    id: int
    status: ServiceOrderStatus
    client_name: str
    vehicle_plate: str
    quote_total: float
    created_at: datetime
    quote_sent_at: datetime | None = None
    approved_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    delivered_at: datetime | None = None


class AverageExecutionTimeRead(BaseModel):
    finished_orders: int
    average_minutes: float
