from app.shared.exceptions import NotFoundError
from app.shared.validators import detect_document_type
from app.slices.clients.domain.entity import ClientEntity
from app.slices.clients.domain.repository import IClientRepository


class ListClientsUseCase:
    def __init__(self, repo: IClientRepository) -> None:
        self._repo = repo

    def execute(self) -> list[ClientEntity]:
        return self._repo.list()


class GetClientUseCase:
    def __init__(self, repo: IClientRepository) -> None:
        self._repo = repo

    def execute(self, client_id: int) -> ClientEntity:
        client = self._repo.get_by_id(client_id)
        if client is None:
            raise NotFoundError("Cliente", client_id)
        return client


class CreateClientUseCase:
    def __init__(self, repo: IClientRepository) -> None:
        self._repo = repo

    def execute(
        self,
        name: str,
        document_number: str,
        email: str | None,
        phone: str | None,
    ) -> ClientEntity:
        document_type = detect_document_type(document_number)
        return self._repo.create(name, document_type, document_number, email, phone)


class UpdateClientUseCase:
    def __init__(self, repo: IClientRepository) -> None:
        self._repo = repo

    def execute(self, client_id: int, fields: dict[str, object]) -> ClientEntity:
        client = self._repo.update(client_id, fields)
        if client is None:
            raise NotFoundError("Cliente", client_id)
        return client


class DeleteClientUseCase:
    def __init__(self, repo: IClientRepository) -> None:
        self._repo = repo

    def execute(self, client_id: int) -> None:
        if not self._repo.delete(client_id):
            raise NotFoundError("Cliente", client_id)
