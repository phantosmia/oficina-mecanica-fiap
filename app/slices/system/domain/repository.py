from abc import ABC, abstractmethod

from app.slices.system.domain.entity import DatabaseStatusEntity


class ISystemRepository(ABC):
    @abstractmethod
    def get_database_status(self) -> DatabaseStatusEntity: ...
