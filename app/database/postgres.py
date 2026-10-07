import psycopg
from psycopg.rows import dict_row

from app.config import settings


def get_connection(timeout: int = 1):
    return psycopg.connect(
        settings.database_url,
        row_factory=dict_row,
        connect_timeout=timeout,
    )


def test_connection(timeout: int = 1) -> bool:
    try:
        with get_connection(timeout=timeout) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 AS result")
                result = cursor.fetchone()

                return result["result"] == 1

    except Exception as exc:
        print(f"PostgreSQL connection failed: {exc}")
        return False