from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from app.config import BASE_DIR, DATA_DIR, DATABASE_PATH, EXPORTS_DIR, PACKAGE_DIR, SCHEMA_PATH
from app.services.admin_service import BACKUPS_DIR, create_database_backup


APP_VERSION = "2026.06.01"


def get_application_settings() -> dict[str, Any]:
    ensure_runtime_directories()
    return {
        "version": APP_VERSION,
        "mode": "Installee" if getattr(sys, "frozen", False) else "Developpement",
        "base_dir": str(BASE_DIR),
        "package_dir": str(PACKAGE_DIR),
        "data_dir": str(DATA_DIR),
        "exports_dir": str(EXPORTS_DIR),
        "backups_dir": str(BACKUPS_DIR),
        "database_path": str(DATABASE_PATH),
        "schema_path": str(SCHEMA_PATH),
        "database_exists": DATABASE_PATH.exists(),
        "database_size": _file_size(DATABASE_PATH),
        "exports_count": _count_files(EXPORTS_DIR, "*.xlsx"),
        "backups_count": _count_files(BACKUPS_DIR, "*.db"),
        "python": sys.version.split()[0],
        "platform": sys.platform,
    }


def ensure_runtime_directories() -> dict[str, str]:
    paths = {
        "data": DATA_DIR,
        "exports": EXPORTS_DIR,
        "backups": BACKUPS_DIR,
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return {key: str(path) for key, path in paths.items()}


def create_settings_backup(label: str | None = None, changed_by: str = "system") -> Path:
    ensure_runtime_directories()
    return create_database_backup(label or "parametres", changed_by=changed_by)


def _file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def _count_files(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.glob(pattern) if item.is_file())
