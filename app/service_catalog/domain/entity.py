from dataclasses import dataclass
from datetime import datetime


@dataclass
class CatalogServiceEntity:
    id: int
    name: str
    description: str | None
    base_price: float
    estimated_minutes: int
    active: bool
    created_at: datetime
    updated_at: datetime | None = None
