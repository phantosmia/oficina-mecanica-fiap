from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.shared.dependencies import get_current_admin
from app.slices.clients.mapper import to_read_model
from app.slices.clients.repository import create_client, delete_client, get_client_by_id, list_clients, update_client
from app.slices.clients.schemas import ClientCreate, ClientRead, ClientUpdate


router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead], dependencies=[Depends(get_current_admin)])
def get_clients() -> list[ClientRead]:
    return [to_read_model(client) for client in list_clients()]


@router.get("/{client_id}", response_model=ClientRead, dependencies=[Depends(get_current_admin)])
def get_client(client_id: int) -> ClientRead:
    client = get_client_by_id(client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    return to_read_model(client)


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
def post_client(payload: ClientCreate) -> ClientRead:
    return to_read_model(create_client(payload.model_dump()))


@router.put("/{client_id}", response_model=ClientRead, dependencies=[Depends(get_current_admin)])
def put_client(client_id: int, payload: ClientUpdate) -> ClientRead:
    client = update_client(client_id, payload.model_dump(exclude_none=True))
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    return to_read_model(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def remove_client(client_id: int) -> Response:
    if not delete_client(client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)