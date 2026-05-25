from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.dependencies import get_current_admin
from app.shared.http_errors import domain_error_handler
from app.slices.clients.adapters.presenter import to_response
from app.slices.clients.adapters.sqlalchemy_repository import SqlAlchemyClientRepository
from app.slices.clients.application.use_cases import (
    CreateClientUseCase,
    DeleteClientUseCase,
    GetClientUseCase,
    ListClientsUseCase,
    UpdateClientUseCase,
)
from app.slices.clients.domain.repository import IClientRepository
from app.slices.clients.schemas import ClientCreate, ClientRead, ClientUpdate

router = APIRouter(prefix="/clients", tags=["clients"])


def _get_repo(session: Session = Depends(get_db)) -> IClientRepository:
    return SqlAlchemyClientRepository(session)


@router.get("", response_model=list[ClientRead], dependencies=[Depends(get_current_admin)])
def get_clients(repo: IClientRepository = Depends(_get_repo)) -> list[ClientRead]:
    return [to_response(c) for c in ListClientsUseCase(repo).execute()]


@router.get("/{client_id}", response_model=ClientRead, dependencies=[Depends(get_current_admin)])
def get_client(client_id: int, repo: IClientRepository = Depends(_get_repo)) -> ClientRead:
    with domain_error_handler():
        return to_response(GetClientUseCase(repo).execute(client_id))


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
def post_client(payload: ClientCreate, repo: IClientRepository = Depends(_get_repo)) -> ClientRead:
    return to_response(
        CreateClientUseCase(repo).execute(
            name=payload.name,
            document_number=payload.document_number,
            email=payload.email,
            phone=payload.phone,
        )
    )


@router.put("/{client_id}", response_model=ClientRead, dependencies=[Depends(get_current_admin)])
def put_client(client_id: int, payload: ClientUpdate, repo: IClientRepository = Depends(_get_repo)) -> ClientRead:
    with domain_error_handler():
        return to_response(UpdateClientUseCase(repo).execute(client_id, payload.model_dump(exclude_none=True)))


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def remove_client(client_id: int, repo: IClientRepository = Depends(_get_repo)) -> Response:
    with domain_error_handler():
        DeleteClientUseCase(repo).execute(client_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
