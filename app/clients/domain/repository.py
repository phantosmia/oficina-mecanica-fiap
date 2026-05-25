from abc import ABC, abstractmethod

from app.clients.domain.entity import ClientEntity


class IClientRepository(ABC):
    @abstractmethod
    def list(self) -> list[ClientEntity]: ...

    @abstractmethod
    def get_by_id(self, client_id: int) -> ClientEntity | None: ...

    @abstractmethod
    def create(
        self,
        name: str,
        document_type: str,
        document_number: str,
        email: str | None,
        phone: str | None,
    ) -> ClientEntity: ...

    @abstractmethod
    def update(self, client_id: int, fields: dict[str, object]) -> ClientEntity | None: ...

    @abstractmethod
    def delete(self, client_id: int) -> bool: ...
