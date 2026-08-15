from app.clients.domain.entity import ClientEntity
from app.clients.schemas import ClientRead


def to_response(entity: ClientEntity) -> ClientRead:
    return ClientRead(
        id=entity.id,
        name=entity.name,
        document_type=entity.document_type,
        document_number=entity.document_number,
        email=entity.email,
        phone=entity.phone,
        status=entity.status,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
