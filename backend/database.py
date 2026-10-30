
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_validation(endpoint, method, status, message):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO validations (endpoint, method, status, message)
            VALUES (?, ?, ?, ?)
            """,
            (endpoint, method, status, message),
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
