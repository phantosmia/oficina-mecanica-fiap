from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PartBase(BaseModel):
    name: str
    sku: str
    description: str | None = None
    unit_price: float = Field(gt=0)
    stock_quantity: int = Field(ge=0)
    min_stock_level: int = Field(ge=0, default=0)


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    name: str | None = None
    sku: str | None = None
    description: str | None = None
    unit_price: float | None = Field(default=None, gt=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    min_stock_level: int | None = Field(default=None, ge=0)


class PartRead(PartBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
