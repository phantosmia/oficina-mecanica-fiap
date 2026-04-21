from app.slices.system.schemas import DatabaseStatus, HealthStatus, RootMessage


def to_root_message(message: str) -> RootMessage:
    return RootMessage(message=message)


def to_health_status(status_text: str) -> HealthStatus:
    return HealthStatus(status=status_text)


def to_database_status(data: dict[str, int | str]) -> DatabaseStatus:
    return DatabaseStatus.model_validate(data)
