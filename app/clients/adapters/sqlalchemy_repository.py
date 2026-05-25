from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.models import Client as ClientORM
from app.clients.domain.entity import ClientEntity
from app.clients.domain.repository import IClientRepository


def _to_entity(orm: ClientORM) -> ClientEntity:
    return ClientEntity(
        id=orm.id,
        name=orm.name,
        document_type=orm.document_type or "",
        document_number=orm.document_number or "",
        email=orm.email,
        phone=orm.phone,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SqlAlchemyClientRepository(IClientRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> list[ClientEntity]:
        return [_to_entity(c) for c in self._session.scalars(select(ClientORM).order_by(ClientORM.id)).all()]

    def get_by_id(self, client_id: int) -> ClientEntity | None:
        orm = self._session.get(ClientORM, client_id)
        return _to_entity(orm) if orm else None

    def create(
        self,
        name: str,
        document_type: str,
        document_number: str,
        email: str | None,
        phone: str | None,
    ) -> ClientEntity:
        client = ClientORM(
            name=name,
            document_type=document_type,
            document_number=document_number,
            email=email,
            phone=phone,
        )
        self._session.add(client)
        self._session.commit()
        self._session.refresh(client)
        return _to_entity(client)

    def update(self, client_id: int, fields: dict[str, object]) -> ClientEntity | None:
        client = self._session.get(ClientORM, client_id)
        if client is None:
            return None
        for key, value in fields.items():
            setattr(client, key, value)
        client.updated_at = datetime.now(UTC)
        self._session.commit()
        self._session.refresh(client)
        return _to_entity(client)

    def delete(self, client_id: int) -> bool:
        client = self._session.get(ClientORM, client_id)
        if client is None:
            return False
        self._session.delete(client)
        self._session.commit()
        return True
