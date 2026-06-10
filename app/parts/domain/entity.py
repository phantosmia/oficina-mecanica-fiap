from dataclasses import dataclass
from datetime import datetime


@dataclass
class PartEntity:
    id: int
    name: str
    sku: str
    description: str | None
    unit_price: float
    stock_quantity: int
    min_stock_level: int
    created_at: datetime
    updated_at: datetime | None = None
