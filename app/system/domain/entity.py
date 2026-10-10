from dataclasses import dataclass


@dataclass
class DatabaseStatusEntity:
    database: str
    connection: str
    clients: int
    vehicles: int
    service_orders: int
