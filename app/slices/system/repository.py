from app.shared.database import DATABASE_PATH, get_connection


def get_database_status() -> dict[str, int | str]:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM clients")
        total_clients = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM vehicles")
        total_vehicles = cursor.fetchone()[0]

    return {
        "database": "sqlite",
        "path": str(DATABASE_PATH),
        "clients": total_clients,
        "vehicles": total_vehicles,
    }