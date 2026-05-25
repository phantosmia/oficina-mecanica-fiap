from dataclasses import dataclass
from datetime import datetime


@dataclass
class VehicleEntity:
    id: int
    client_id: int
    brand: str
    model: str
    year: int
    license_plate: str
    created_at: datetime
    updated_at: datetime | None = None
