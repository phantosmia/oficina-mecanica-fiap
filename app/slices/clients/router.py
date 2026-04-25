from fastapi import APIRouter, Depends, Response, status

from app.shared.dependencies import get_current_admin
from app.slices.clients.mapper import to_read_model
from app.slices.clients.schemas import ClientCreate, ClientRead, ClientUpdate
from app.slices.clients import service


router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead], dependencies=[Depends(get_current_admin)])
def get_clients() -> list[ClientRead]:
    return [to_read_model(client) for client in service.list_clients()]


@router.get("/{client_id}", response_model=ClientRead, dependencies=[Depends(get_current_admin)])
def get_client(client_id: int) -> ClientRead:
    return to_read_model(service.get_client_by_id(client_id))


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
def post_client(payload: ClientCreate) -> ClientRead:
    return to_read_model(service.create_client(payload.model_dump()))


@router.put("/{client_id}", response_model=ClientRead, dependencies=[Depends(get_current_admin)])
def put_client(client_id: int, payload: ClientUpdate) -> ClientRead:
    return to_read_model(service.update_client(client_id, payload.model_dump(exclude_none=True)))


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def remove_client(client_id: int) -> Response:
    service.delete_client(client_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)