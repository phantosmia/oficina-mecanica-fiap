from abc import ABC, abstractmethod

from app.system.domain.entity import DatabaseStatusEntity


class ISystemRepository(ABC):
    @abstractmethod
    def get_database_status(self) -> DatabaseStatusEntity: ...
