from datetime import UTC, datetime

from sqlalchemy import select

from app.shared.database import get_session
from app.shared.models import Client
from app.shared.validators import detect_document_type


def list_clients() -> list[Client]:
    with get_session() as session:
        return list(session.scalars(select(Client).order_by(Client.id)).all())


def get_client_by_id(client_id: int) -> Client | None:
    with get_session() as session:
        return session.get(Client, client_id)


def create_client(payload: dict[str, object]) -> Client:
    with get_session() as session:
        client = Client(
            name=str(payload["name"]),
            document_type=detect_document_type(str(payload["document_number"])),
            document_number=str(payload["document_number"]),
            email=payload.get("email"),
            phone=payload.get("phone"),
        )
        session.add(client)
        session.commit()
        session.refresh(client)
        return client


def update_client(client_id: int, payload: dict[str, object]) -> Client | None:
    with get_session() as session:
        client = session.get(Client, client_id)
        if client is None:
            return None

        for key, value in payload.items():
            setattr(client, key, value)
        client.updated_at = datetime.now(UTC)
        session.commit()
        session.refresh(client)
        return client


def delete_client(client_id: int) -> bool:
    with get_session() as session:
        client = session.get(Client, client_id)
        if client is None:
            return False

        session.delete(client)
        session.commit()
        return True