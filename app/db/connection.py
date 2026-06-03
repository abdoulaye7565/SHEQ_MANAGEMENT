import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.config import DATABASE_PATH, DATA_DIR, SCHEMA_PATH
from app.db.migrations import run_lightweight_migrations


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    _configure_connection(connection)
    return connection


def initialize_database() -> None:
    has_existing_schema = DATABASE_PATH.exists()
    connection = get_connection()
    try:
        if not has_existing_schema or not _has_core_schema(connection):
            schema = SCHEMA_PATH.read_text(encoding="utf-8")
            connection.executescript(schema)
        run_lightweight_migrations(connection)
        connection.commit()
    finally:
        connection.close()


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _configure_connection(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute("PRAGMA cache_size = -20000")
    connection.execute("PRAGMA mmap_size = 268435456")


def _has_core_schema(connection: sqlite3.Connection) -> bool:
    required_tables = {"employes", "presences", "employee_breaks", "sites", "fonctions"}
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name IN ('employes', 'presences', 'employee_breaks', 'sites', 'fonctions')
        """
    ).fetchall()
    return {str(row["name"]) for row in rows} == required_tables
