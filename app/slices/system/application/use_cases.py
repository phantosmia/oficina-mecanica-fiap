from app.slices.system.domain.entity import DatabaseStatusEntity
from app.slices.system.domain.repository import ISystemRepository


class GetDatabaseStatusUseCase:
    def __init__(self, repo: ISystemRepository) -> None:
        self._repo = repo

    def execute(self) -> DatabaseStatusEntity:
        return self._repo.get_database_status()
