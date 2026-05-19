import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    PACKAGE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    PACKAGE_DIR = BASE_DIR

DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
DATABASE_PATH = DATA_DIR / "orezone.db"
SCHEMA_PATH = PACKAGE_DIR / "app" / "db" / "schema.sql"
