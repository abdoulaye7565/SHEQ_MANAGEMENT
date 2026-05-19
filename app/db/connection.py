import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.config import DATABASE_PATH, DATA_DIR, SCHEMA_PATH


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    connection = get_connection()
    try:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        connection.executescript(schema)
        _run_lightweight_migrations(connection)
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


def _run_lightweight_migrations(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS departments (
            id_department INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            description TEXT,
            actif INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
        """
    )
    _add_column_if_missing(connection, "sites", "department_id", "INTEGER")
    _add_column_if_missing(connection, "employes", "nom", "TEXT")
    _add_column_if_missing(connection, "employes", "prenom", "TEXT")
    _add_column_if_missing(connection, "employes", "departure_type", "TEXT")
    _add_column_if_missing(connection, "employes", "departure_date", "TEXT")
    _add_column_if_missing(connection, "employes", "departure_comment", "TEXT")
    _add_column_if_missing(connection, "badges", "date_expiration", "TEXT")
    _add_column_if_missing(
        connection,
        "presences",
        "statut_presence",
        "TEXT NOT NULL DEFAULT 'absent'",
    )
    _add_column_if_missing(connection, "formations", "structure_responsable", "TEXT")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_breaks (
            id_break INTEGER PRIMARY KEY AUTOINCREMENT,
            employe_id INTEGER NOT NULL,
            type_break TEXT NOT NULL,
            date_debut TEXT NOT NULL,
            date_fin TEXT NOT NULL,
            statut TEXT NOT NULL DEFAULT 'planifie',
            commentaire TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (employe_id) REFERENCES employes(id_employe),
            CHECK (type_break IN ('break', 'permission', 'sick', 'annual')),
            CHECK (statut IN ('planifie', 'en_cours', 'termine', 'annule'))
        )
        """
    )
    _rebuild_employee_breaks_type_check_if_needed(connection)
    _deduplicate_employee_trainings(connection)
    _deduplicate_daily_themes(connection)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS toolbox_theme_catalog (
            id_topic INTEGER PRIMARY KEY AUTOINCREMENT,
            theme TEXT NOT NULL UNIQUE,
            obligatoire INTEGER NOT NULL DEFAULT 0,
            actif INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_themes_securite_date
        ON themes_securite(date_theme)
        """
    )
    connection.execute(
        """
        UPDATE training_types
        SET validite_mois = 24,
            updated_at = CURRENT_TIMESTAMP
        WHERE validite_mois <> 24
        """
    )
    connection.execute(
        """
        UPDATE badges
        SET date_expiration = DATE(date_remise, '+2 years'),
            updated_at = CURRENT_TIMESTAMP
        WHERE date_remise IS NOT NULL
          AND date_remise <> ''
          AND (
              date_expiration IS NULL
              OR date_expiration = ''
              OR date_expiration <> DATE(date_remise, '+2 years')
          )
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_formations_unique_employee_type
        ON formations(employe_id, type_training_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_employee_breaks_employe_dates
        ON employee_breaks(employe_id, date_debut, date_fin)
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance_day_locks (
            date_presence TEXT PRIMARY KEY,
            locked_by TEXT NOT NULL DEFAULT 'system',
            locked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            commentaire TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_site_assignments (
            id_assignment INTEGER PRIMARY KEY AUTOINCREMENT,
            employe_id INTEGER NOT NULL,
            site_id INTEGER NOT NULL,
            date_debut TEXT NOT NULL,
            date_fin TEXT,
            motif TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (employe_id) REFERENCES employes(id_employe),
            FOREIGN KEY (site_id) REFERENCES sites(id_site),
            CHECK (date_fin IS NULL OR date_fin >= date_debut)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_employee_site_assignments_employee_dates
        ON employee_site_assignments(employe_id, date_debut, date_fin)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_employee_site_assignments_site_dates
        ON employee_site_assignments(site_id, date_debut, date_fin)
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS role_module_permissions (
            role_id INTEGER NOT NULL,
            module_key TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (role_id, module_key),
            FOREIGN KEY (role_id) REFERENCES roles(id_role)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_audit (
            id_audit INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            cible_type TEXT,
            cible_id TEXT,
            ancienne_valeur TEXT,
            nouvelle_valeur TEXT,
            changed_by TEXT NOT NULL DEFAULT 'system',
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            commentaire TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance_audit (
            id_audit INTEGER PRIMARY KEY AUTOINCREMENT,
            presence_id INTEGER,
            employe_id INTEGER NOT NULL,
            date_presence TEXT NOT NULL,
            champ TEXT NOT NULL,
            ancienne_valeur TEXT,
            nouvelle_valeur TEXT,
            changed_by TEXT NOT NULL DEFAULT 'system',
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            commentaire TEXT,
            FOREIGN KEY (presence_id) REFERENCES presences(id_presence),
            FOREIGN KEY (employe_id) REFERENCES employes(id_employe)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS timesheet_day_settings (
            date_presence TEXT PRIMARY KEY,
            has_drilling INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            commentaire TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS timesheet_day_overrides (
            employe_id INTEGER NOT NULL,
            date_presence TEXT NOT NULL,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            commentaire TEXT,
            PRIMARY KEY (employe_id, date_presence),
            FOREIGN KEY (employe_id) REFERENCES employes(id_employe),
            CHECK (status IN ('rest', 'absent'))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS timesheet_month_locks (
            month TEXT PRIMARY KEY,
            locked_by TEXT NOT NULL DEFAULT 'system',
            locked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            commentaire TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS timesheet_audit (
            id_audit INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            date_presence TEXT,
            employe_id INTEGER,
            action TEXT NOT NULL,
            ancienne_valeur TEXT,
            nouvelle_valeur TEXT,
            changed_by TEXT NOT NULL DEFAULT 'system',
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            commentaire TEXT,
            FOREIGN KEY (employe_id) REFERENCES employes(id_employe)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_timesheet_audit_month
        ON timesheet_audit(month, date_presence, employe_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_timesheet_day_overrides_date
        ON timesheet_day_overrides(date_presence, employe_id)
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS epi_inspections (
            id_inspection INTEGER PRIMARY KEY AUTOINCREMENT,
            epi_id INTEGER NOT NULL,
            date_inspection TEXT NOT NULL,
            statut TEXT NOT NULL DEFAULT 'ok',
            prochaine_inspection TEXT,
            inspecteur TEXT,
            observations TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (epi_id) REFERENCES epi(id_epi),
            CHECK (statut IN ('ok', 'a_surveiller', 'endommage', 'hors_service'))
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_epi_inspections_epi_date
        ON epi_inspections(epi_id, date_inspection)
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS shift_templates (
            id_template INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_code TEXT NOT NULL UNIQUE,
            libelle TEXT NOT NULL,
            heure_entree TEXT NOT NULL,
            heure_sortie TEXT NOT NULL,
            actif INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            CHECK (shift_code IN ('DAY', 'NIGHT', 'BREAK'))
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_attendance_audit_date
        ON attendance_audit(date_presence, employe_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_audit_changed_at
        ON admin_audit(changed_at, action)
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO shift_templates(shift_code, libelle, heure_entree, heure_sortie, actif) VALUES
            ('DAY', 'Travaux drilling 06-18', '06:00', '18:00', 1),
            ('NIGHT', 'Sans drilling 06-14', '06:00', '14:00', 1),
            ('BREAK', 'Hors service', '00:00', '00:00', 1)
        """
    )
    connection.execute(
        """
        UPDATE shift_templates
        SET libelle = 'Travaux drilling 06-18',
            heure_entree = '06:00',
            heure_sortie = '18:00',
            updated_at = CURRENT_TIMESTAMP
        WHERE shift_code = 'DAY'
        """
    )
    connection.execute(
        """
        UPDATE shift_templates
        SET libelle = 'Sans drilling 06-14',
            heure_entree = '06:00',
            heure_sortie = '14:00',
            updated_at = CURRENT_TIMESTAMP
        WHERE shift_code = 'NIGHT'
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS training_departments (
            id_department INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            actif INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO training_departments(nom, actif) VALUES
            ('HSE', 1),
            ('Ressources humaines', 1),
            ('Operations', 1),
            ('Maintenance', 1),
            ('Mine', 1),
            ('Administration', 1),
            ('Sous-traitant', 1),
            ('Externe', 1)
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO departments(nom, description, actif) VALUES
            ('Geologie', 'Departement geologie et operations terrain', 1)
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO sites(nom, localisation, department_id, actif)
        SELECT 'SYAMA', 'Site par defaut - departement Geologie', d.id_department, 1
        FROM departments d
        WHERE d.nom = 'Geologie'
        """
    )
    connection.execute(
        """
        UPDATE sites
        SET department_id = (SELECT id_department FROM departments WHERE nom = 'Geologie'),
            updated_at = CURRENT_TIMESTAMP
        WHERE nom = 'SYAMA'
          AND department_id IS NULL
        """
    )
    connection.execute(
        """
        INSERT INTO employee_site_assignments(employe_id, site_id, date_debut, motif)
        SELECT e.id_employe, e.site_id, DATE(e.created_at), 'Affectation initiale'
        FROM employes e
        WHERE NOT EXISTS (
            SELECT 1
            FROM employee_site_assignments esa
            WHERE esa.employe_id = e.id_employe
        )
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO role_module_permissions(role_id, module_key)
        SELECT id_role, 'MonthlyTimesheet'
        FROM roles
        WHERE nom IN ('Administrateur', 'Superviseur')
        """
    )


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _rebuild_employee_breaks_type_check_if_needed(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'employee_breaks'"
    ).fetchone()
    sql = row["sql"] or "" if row else ""
    if not row or ("'sick'" in sql and "'annual'" in sql):
        return

    connection.execute("ALTER TABLE employee_breaks RENAME TO employee_breaks_old")
    connection.execute(
        """
        CREATE TABLE employee_breaks (
            id_break INTEGER PRIMARY KEY AUTOINCREMENT,
            employe_id INTEGER NOT NULL,
            type_break TEXT NOT NULL,
            date_debut TEXT NOT NULL,
            date_fin TEXT NOT NULL,
            statut TEXT NOT NULL DEFAULT 'planifie',
            commentaire TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (employe_id) REFERENCES employes(id_employe),
            CHECK (type_break IN ('break', 'permission', 'sick', 'annual')),
            CHECK (statut IN ('planifie', 'en_cours', 'termine', 'annule'))
        )
        """
    )
    connection.execute(
        """
        INSERT INTO employee_breaks (
            id_break, employe_id, type_break, date_debut, date_fin, statut,
            commentaire, created_at, updated_at
        )
        SELECT
            id_break, employe_id, type_break, date_debut, date_fin, statut,
            commentaire, created_at, updated_at
        FROM employee_breaks_old
        """
    )
    connection.execute("DROP TABLE employee_breaks_old")


def _deduplicate_employee_trainings(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        DELETE FROM formations
        WHERE id_formation IN (
            SELECT old.id_formation
            FROM formations old
            JOIN formations keep
              ON keep.employe_id = old.employe_id
             AND keep.type_training_id = old.type_training_id
             AND (
                 keep.date_expiration > old.date_expiration
                 OR (
                     keep.date_expiration = old.date_expiration
                     AND keep.id_formation > old.id_formation
                 )
             )
        )
        """
    )


def _deduplicate_daily_themes(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        DELETE FROM themes_securite
        WHERE id_theme IN (
            SELECT old.id_theme
            FROM themes_securite old
            JOIN themes_securite keep
              ON keep.date_theme = old.date_theme
             AND keep.id_theme > old.id_theme
        )
        """
    )
