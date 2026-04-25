from fastapi import HTTPException, status

from app.shared.models import Client
from app.slices.clients import repository


def list_clients() -> list[Client]:
    return repository.list_clients()


def get_client_by_id(client_id: int) -> Client:
    client = repository.get_client_by_id(client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    return client


def create_client(payload: dict[str, object]) -> Client:
    return repository.create_client(payload)


def update_client(client_id: int, payload: dict[str, object]) -> Client:
    client = repository.update_client(client_id, payload)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    return client


def delete_client(client_id: int) -> None:
    if not repository.delete_client(client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
