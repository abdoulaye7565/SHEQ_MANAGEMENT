import sys
from pathlib import Path
import os

ALL_MODULES = [
    "Dashboard",
    "Referentials",
    "EmployeeManagement",
    "TrainingManagement",
    "ToolboxTalk",
    "TimeSheet",
    "MonthlyTimesheet",
    "Ppe",
    "MaintenanceActions",
    "Alerts",
    "AiAssistant",
    "Settings",
    "Admin",
]

ROLE_MODULES: dict[str, list[str]] = {
    "Administrateur": list(ALL_MODULES),
    "Officier HSE": ["Dashboard", "TrainingManagement", "ToolboxTalk", "MaintenanceActions", "Alerts", "AiAssistant"],
    "Superviseur": ["Dashboard", "EmployeeManagement", "ToolboxTalk", "TimeSheet", "MonthlyTimesheet", "MaintenanceActions", "Alerts"],
    "Responsable stock": ["Dashboard", "Ppe", "MaintenanceActions", "Alerts"],
    "Direction": ["Dashboard", "MaintenanceActions", "Alerts", "AiAssistant"],
}


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    PACKAGE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    PACKAGE_DIR = BASE_DIR

if getattr(sys, "frozen", False):
    runtime_root = Path(os.getenv("OREZONE_QHSE_HOME") or os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
    DATA_DIR = runtime_root / "OREZONE_QHSE" / "data"
else:
    DATA_DIR = BASE_DIR / "data"
if getattr(sys, "frozen", False):
    EXPORTS_DIR = Path.home() / "Documents" / "OREZONE_QHSE" / "exports"
else:
    EXPORTS_DIR = BASE_DIR / "exports"
DATABASE_PATH = DATA_DIR / "orezone.db"
SCHEMA_PATH = PACKAGE_DIR / "app" / "db" / "schema.sql"
LOGS_DIR = DATA_DIR.parent / "logs"
