from app.shared.models import Client
from app.slices.clients.schemas import ClientRead


def to_read_model(client: Client) -> ClientRead:
    return ClientRead.model_validate(client)
