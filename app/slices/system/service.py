from app.slices.system import repository


def get_root_message() -> str:
    return "Oficina Mecânica FIAP API pronta para gestão de ordens de serviço"


def get_health_status() -> str:
    return "ok"


def get_database_status() -> dict[str, int | str]:
    return repository.get_database_status()
