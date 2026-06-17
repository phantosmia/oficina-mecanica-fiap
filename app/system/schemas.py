from pydantic import BaseModel


class RootMessage(BaseModel):
    message: str


class HealthStatus(BaseModel):
    status: str


class DatabaseStatus(BaseModel):
    database: str
    connection: str
    clients: int
    vehicles: int
    services: int
    parts: int
    service_orders: int