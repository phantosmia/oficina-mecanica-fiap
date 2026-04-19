from app.shared.database import get_connection


def list_vehicles() -> list[dict[str, object]]:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, client_id, brand, model, year, license_plate, created_at
            FROM vehicles
            ORDER BY id
            """
        )
        rows = cursor.fetchall()

    return [dict(row) for row in rows]