from pydantic import BaseModel


class RootMessage(BaseModel):
    message: str


class HealthStatus(BaseModel):
    status: str


class DatabaseStatus(BaseModel):
    database: str
    path: str
    clients: int
    vehicles: int