from __future__ import annotations

import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_RELEASE_SUFFIXES = (".db", ".db-wal", ".db-shm")


def main() -> int:
    errors: list[str] = []
    release_zip = ROOT / "dist" / "OREZONE_QHSE_INSTALLABLE.zip"
    if release_zip.exists():
        with zipfile.ZipFile(release_zip) as archive:
            forbidden = [
                name
                for name in archive.namelist()
                if name.lower().endswith(FORBIDDEN_RELEASE_SUFFIXES)
            ]
        if forbidden:
            errors.append(f"Le paquet Windows contient une base SQLite: {forbidden[0]}")

    tracked_sensitive = [
        ROOT / "data" / "ai_config.json",
        ROOT / "data" / "email_config.json",
        ROOT / "data" / "mobile_sync_config.json",
    ]
    for path in tracked_sensitive:
        if path.exists() and not _is_ignored(path):
            errors.append(f"Configuration sensible non ignoree par Git: {path.relative_to(ROOT)}")

    if errors:
        print("\n".join(f"ERROR: {message}" for message in errors))
        return 1
    print("Release policy OK: aucun fichier sensible detecte.")
    return 0


def _is_ignored(path: Path) -> bool:
    import subprocess

    result = subprocess.run(
        ["git", "check-ignore", "-q", str(path.relative_to(ROOT))],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


if __name__ == "__main__":
    sys.exit(main())
