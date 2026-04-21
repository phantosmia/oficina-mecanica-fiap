from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CatalogServiceBase(BaseModel):
    name: str
    description: str | None = None
    base_price: float = Field(gt=0)
    estimated_minutes: int = Field(gt=0)
    active: bool = True


class CatalogServiceCreate(CatalogServiceBase):
    pass


class CatalogServiceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    base_price: float | None = Field(default=None, gt=0)
    estimated_minutes: int | None = Field(default=None, gt=0)
    active: bool | None = None


class CatalogServiceRead(CatalogServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
