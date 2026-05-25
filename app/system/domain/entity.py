from dataclasses import dataclass


@dataclass
class DatabaseStatusEntity:
    database: str
    path: str
    clients: int
    vehicles: int
    services: int
    parts: int
    service_orders: int
