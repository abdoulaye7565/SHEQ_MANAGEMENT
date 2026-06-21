import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager

from app.config import DATABASE_PATH, DATA_DIR, SCHEMA_PATH
from app.db.migrations import run_lightweight_migrations

_DB_LOCKED_DELAYS = (0.2, 0.5, 1.0)


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    _configure_connection(connection)
    return connection


def initialize_database() -> None:
    from app.services.toolbox_talk_service import run_bilingual_normalization_once

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
    run_bilingual_normalization_once()


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except sqlite3.OperationalError as exc:
        connection.rollback()
        if "database is locked" in str(exc).lower():
            raise sqlite3.OperationalError(
                "La base de donnees est occupee. Fermez les autres fenetres de l'application et reessayez."
            ) from exc
        raise
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@contextmanager
def db_session_with_retry(max_retries: int = 3) -> Iterator[sqlite3.Connection]:
    """Context manager que retente la connexion en cas de verrou base de donnees."""
    last_exc: sqlite3.OperationalError | None = None
    delays = list(_DB_LOCKED_DELAYS[:max_retries])

    for attempt, delay in enumerate(delays):
        connection = get_connection()
        try:
            yield connection
            connection.commit()
            return
        except sqlite3.OperationalError as exc:
            connection.rollback()
            connection.close()
            if "database is locked" in str(exc).lower() and attempt < len(delays) - 1:
                last_exc = exc
                time.sleep(delay)
                continue
            raise
        except Exception:
            connection.rollback()
            connection.close()
            raise
        finally:
            try:
                connection.close()
            except Exception:
                pass

    raise sqlite3.OperationalError(
        "Base de donnees verrouillee apres plusieurs tentatives. Reessayez dans quelques secondes."
    ) from last_exc


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
