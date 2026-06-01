from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import connection


EMPLOYEES = [
    ("OZ0008", "HAMARA I", "KANOUTE", "ASSISTANT DRILLER"),
    ("OZ0004", "Dembele", "Bakary", "Driller"),
    ("OZ0009", "ABDOU", "DEMBELE", "ASSISTANT DRILLER"),
    ("OZ0014", "ADAMA", "CAMARA", "ASSISTANT DRILLER"),
    ("OZ0013", "MASSAOUL", "SAMAKE", "ASSISTANT DRILLER"),
    ("OZ0005", "Sissoko", "Yakare-Makan", "Operateur"),
    ("OZ0007", "ISIDOR", "SISSOKO", "ASSISTANT DRILLER"),
    ("OZ0012", "KARIM", "DIALLO", "ASSISTANT DRILLER"),
    ("OZ0002", "SAYON", "DIARRA", "ASSISTANT DRILLER"),
    ("OZ0011", "Coulibaly", "Souadou", "Operateur"),
    ("OZ0006", "MAMOUDOU", "DIALLO", "ASSISTANT DRILLER"),
    ("OZ0003", "SALIF", "BAMBA", "ASSISTANT DRILLER"),
    ("OZ0010", "DJOUNGO", "DOUCOURE", "DRILLER"),
    ("OZ0001", "ABOU", "DIARRA", "SAFETY"),
    ("OZ0020", "OUSMANE", "SANOGO", "DRIVER"),
    ("OZ0015", "Traore", "Mamady", "Driver"),
    ("OZ0016", "FOUSSEYNI", "DIALLO", "DRIVER"),
    ("OZ0019", "BADOUMANTIE", "KONE", "RC SUPERVISOR"),
    ("OZ0021", "SOUMAILA", "CAMARA", "RC DRILLER"),
    ("OZ0017", "LADI SIAKA", "COULIBALY", "RC DRILLER"),
    ("OZ0018", "DAOUDA", "COULIBALY", "RC DRILLER"),
    ("OZ0022", "MAMADOU", "FOFANA", "MECHANIC"),
]


DEPENDENT_TABLES = [
    "attendance_audit",
    "timesheet_audit",
    "timesheet_day_overrides",
    "presences",
    "employee_breaks",
    "formations",
    "badges",
    "affectations_epi",
    "historique_shifts",
    "employee_site_assignments",
]


def main() -> None:
    connection.initialize_database()
    backup_path = _backup_database()
    with connection.db_session() as db:
        site_id = _ensure_syama_site(db)
        shift_id = _shift_id(db)
        group_id = _default_group_id(db)
        function_ids = {
            function_name: _ensure_function(db, function_name)
            for _, _, _, function_name in EMPLOYEES
        }
        for table in DEPENDENT_TABLES:
            db.execute(f"DELETE FROM {table}")
        db.execute("DELETE FROM employes")
        for matricule, nom, prenom, fonction in EMPLOYEES:
            full_name = f"{nom} {prenom}".strip()
            cursor = db.execute(
                """
                INSERT INTO employes (
                    matricule, nom, prenom, nom_complet, fonction_id, site_id,
                    groupe_id, shift_id, type_employe, statut
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'national', 'actif')
                """,
                (
                    matricule,
                    nom,
                    prenom,
                    full_name,
                    function_ids[fonction],
                    site_id,
                    group_id,
                    shift_id,
                ),
            )
            db.execute(
                """
                INSERT INTO employee_site_assignments(employe_id, site_id, date_debut, motif)
                VALUES (?, ?, DATE('now'), 'Chargement liste TimeSheet image')
                """,
                (int(cursor.lastrowid), site_id),
            )
    print(f"{len(EMPLOYEES)} employes inseres. Sauvegarde: {backup_path}")


def _backup_database() -> str:
    if not connection.DATABASE_PATH.exists():
        return "aucune base existante"
    backup_dir = connection.DATABASE_PATH.parent.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"orezone_backup_{timestamp}_before_replace_image_employees.db"
    shutil.copy2(connection.DATABASE_PATH, backup_path)
    return str(backup_path)


def _ensure_syama_site(db) -> int:
    department = db.execute("SELECT id_department FROM departments WHERE nom = 'Geologie'").fetchone()
    if department is None:
        cursor = db.execute("INSERT INTO departments(nom, description, actif) VALUES ('Geologie', 'Geologie', 1)")
        department_id = int(cursor.lastrowid)
    else:
        department_id = int(department["id_department"])
    site = db.execute("SELECT id_site FROM sites WHERE nom = 'SYAMA'").fetchone()
    if site:
        db.execute("UPDATE sites SET department_id = ?, actif = 1 WHERE id_site = ?", (department_id, site["id_site"]))
        return int(site["id_site"])
    cursor = db.execute(
        "INSERT INTO sites(nom, localisation, department_id, actif) VALUES ('SYAMA', 'SYAMA', ?, 1)",
        (department_id,),
    )
    return int(cursor.lastrowid)


def _shift_id(db) -> int:
    row = db.execute("SELECT id_shift FROM shifts WHERE code = 'DAY'").fetchone()
    if row is None:
        cursor = db.execute("INSERT INTO shifts(code, libelle, actif) VALUES ('DAY', 'Day Shift', 1)")
        return int(cursor.lastrowid)
    return int(row["id_shift"])


def _default_group_id(db) -> int | None:
    row = db.execute("SELECT id_groupe FROM groupes WHERE actif = 1 ORDER BY id_groupe LIMIT 1").fetchone()
    return int(row["id_groupe"]) if row else None


def _ensure_function(db, name: str) -> int:
    normalized = name.upper()
    row = db.execute("SELECT id_fonction FROM fonctions WHERE UPPER(nom) = ?", (normalized,)).fetchone()
    if row:
        return int(row["id_fonction"])
    cursor = db.execute("INSERT INTO fonctions(nom, description, actif) VALUES (?, ?, 1)", (name, name))
    return int(cursor.lastrowid)


if __name__ == "__main__":
    main()
