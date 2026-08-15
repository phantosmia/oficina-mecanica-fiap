from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.shared.validators import detect_document_type, validate_document
from app.clients.domain.value_objects import ClientStatus


class ClientBase(BaseModel):
    name: str
    document_number: str
    email: EmailStr | None = None
    phone: str | None = None

    @field_validator("document_number")
    @classmethod
    def validate_document_number(cls, value: str) -> str:
        return validate_document(value)


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    status: ClientStatus | None = None


class ClientRead(ClientBase):
    id: int
    document_type: str
    status: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)