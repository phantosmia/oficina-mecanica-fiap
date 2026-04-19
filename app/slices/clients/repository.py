from app.shared.database import get_connection


def list_clients() -> list[dict[str, object]]:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, name, email, phone, created_at
            FROM clients
            ORDER BY id
            """
        )
        rows = cursor.fetchall()

    return [dict(row) for row in rows]