from dataclasses import dataclass
from datetime import datetime


@dataclass
class ClientEntity:
    id: int
    name: str
    document_type: str
    document_number: str
    email: str | None
    phone: str | None
    created_at: datetime
    updated_at: datetime | None = None
    status: str = "ativo"
