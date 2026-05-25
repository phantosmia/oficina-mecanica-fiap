from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.validators import validate_plate


class VehicleBase(BaseModel):
    client_id: int
    brand: str
    model: str
    year: int = Field(ge=1900, le=2100)
    license_plate: str

    @field_validator("license_plate")
    @classmethod
    def validate_license_plate(cls, value: str) -> str:
        return validate_plate(value)


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    client_id: int | None = None
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    license_plate: str | None = None


class VehicleRead(VehicleBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)