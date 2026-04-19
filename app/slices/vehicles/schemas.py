from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VehicleBase(BaseModel):
    client_id: int
    brand: str | None = None
    model: str
    year: int | None = None
    license_plate: str | None = None


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

    model_config = ConfigDict(from_attributes=True)