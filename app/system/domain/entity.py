from dataclasses import dataclass


@dataclass
class DatabaseStatusEntity:
    database: str
    connection: str
    clients: int
    vehicles: int
    services: int
    parts: int
    service_orders: int
