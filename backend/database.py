
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "contractiq.db"


def init_db():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                http_status INTEGER,
                response_time_ms REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Safely add new columns to an existing database
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(validations)"
            ).fetchall()
        }

        if "http_status" not in columns:
            connection.execute(
                "ALTER TABLE validations ADD COLUMN http_status INTEGER"
            )

        if "response_time_ms" not in columns:
            connection.execute(
                "ALTER TABLE validations ADD COLUMN response_time_ms REAL"
            )


def save_validation(
    endpoint,
    method,
    status,
    message,
    http_status=None,
    response_time_ms=None
):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO validations (
                endpoint,
                method,
                status,
                message,
                http_status,
                response_time_ms
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                endpoint,
                method,
                status,
                message,
                http_status,
                response_time_ms
            ),
        )


def get_history():
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM validations ORDER BY id DESC"
        ).fetchall()

        return [dict(row) for row in rows]


def clear_history():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("DELETE FROM validations")
