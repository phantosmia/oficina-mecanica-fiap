from fastapi import APIRouter

from app.slices.clients.repository import list_clients
from app.slices.clients.schemas import ClientRead


router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
def get_clients() -> list[ClientRead]:
    return [ClientRead.model_validate(client) for client in list_clients()]