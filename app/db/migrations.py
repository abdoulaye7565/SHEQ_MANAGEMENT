from __future__ import annotations

import sqlite3


def run_lightweight_migrations(connection: sqlite3.Connection) -> None:
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
    _add_column_if_missing(connection, "timesheet_day_settings", "day_type", "TEXT NOT NULL DEFAULT 'work'")
    _add_column_if_missing(connection, "badges", "date_expiration", "TEXT")
    _add_column_if_missing(connection, "training_types", "department_id", "INTEGER")
    _add_column_if_missing(
        connection,
        "presences",
        "statut_presence",
        "TEXT NOT NULL DEFAULT 'absent'",
    )
    _add_column_if_missing(connection, "formations", "structure_responsable", "TEXT")
    _add_column_if_missing(connection, "equipment_maintenance", "current_odometer", "REAL")
    _add_column_if_missing(connection, "equipment_maintenance", "last_service_odometer", "REAL")
    _add_column_if_missing(connection, "equipment_maintenance", "service_interval_km", "REAL")
    _add_column_if_missing(connection, "equipment_maintenance", "next_due_odometer", "REAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS equipment_monthly_checks (
            month TEXT PRIMARY KEY,
            confirmed_by TEXT NOT NULL DEFAULT 'system',
            confirmed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            commentaire TEXT
        )
        """
    )
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
    _rebuild_equipment_maintenance_type_check_if_needed(connection)
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
    _ensure_performance_indexes(connection)
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
            day_type TEXT NOT NULL DEFAULT 'work',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            commentaire TEXT,
            CHECK (day_type IN ('work', 'holiday'))
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
        CREATE TABLE IF NOT EXISTS equipment_maintenance (
            id_maintenance INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_code TEXT,
            equipment_name TEXT NOT NULL,
            category TEXT,
            site_id INTEGER,
            responsible_employee_id INTEGER,
            maintenance_type TEXT NOT NULL DEFAULT 'preventive',
            priority TEXT NOT NULL DEFAULT 'moyenne',
            status TEXT NOT NULL DEFAULT 'planifiee',
            planned_date TEXT NOT NULL,
            completed_date TEXT,
            next_due_date TEXT,
            current_odometer REAL,
            last_service_odometer REAL,
            service_interval_km REAL,
            next_due_odometer REAL,
            cost REAL NOT NULL DEFAULT 0,
            observations TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (site_id) REFERENCES sites(id_site),
            FOREIGN KEY (responsible_employee_id) REFERENCES employes(id_employe),
            CHECK (maintenance_type IN ('preventive', 'corrective', 'inspection', 'calibration', 'oil_change')),
            CHECK (priority IN ('basse', 'moyenne', 'haute', 'critique')),
            CHECK (status IN ('planifiee', 'en_cours', 'terminee', 'annulee', 'en_retard')),
            CHECK (completed_date IS NULL OR completed_date >= planned_date)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS action_tracker (
            id_action INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL DEFAULT 'HSE',
            title TEXT NOT NULL,
            description TEXT,
            site_id INTEGER,
            owner_employee_id INTEGER,
            priority TEXT NOT NULL DEFAULT 'moyenne',
            status TEXT NOT NULL DEFAULT 'ouverte',
            due_date TEXT NOT NULL,
            closed_date TEXT,
            progress INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (site_id) REFERENCES sites(id_site),
            FOREIGN KEY (owner_employee_id) REFERENCES employes(id_employe),
            CHECK (priority IN ('basse', 'moyenne', 'haute', 'critique')),
            CHECK (status IN ('ouverte', 'en_cours', 'terminee', 'annulee', 'en_retard')),
            CHECK (progress >= 0 AND progress <= 100),
            CHECK (closed_date IS NULL OR closed_date >= due_date)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_assessments (
            id_risk INTEGER PRIMARY KEY AUTOINCREMENT,
            activity TEXT NOT NULL,
            task TEXT,
            hazard TEXT NOT NULL,
            risk_event TEXT NOT NULL,
            consequences TEXT NOT NULL,
            existing_controls TEXT,
            site_id INTEGER,
            owner_employee_id INTEGER,
            probability_initial INTEGER NOT NULL DEFAULT 1,
            severity_initial INTEGER NOT NULL DEFAULT 1,
            risk_initial INTEGER NOT NULL DEFAULT 1,
            level_initial TEXT NOT NULL DEFAULT 'low',
            hierarchy_control TEXT NOT NULL DEFAULT 'administrative',
            additional_controls TEXT,
            probability_residual INTEGER NOT NULL DEFAULT 1,
            severity_residual INTEGER NOT NULL DEFAULT 1,
            risk_residual INTEGER NOT NULL DEFAULT 1,
            level_residual TEXT NOT NULL DEFAULT 'low',
            status TEXT NOT NULL DEFAULT 'open',
            due_date TEXT,
            review_date TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (site_id) REFERENCES sites(id_site),
            FOREIGN KEY (owner_employee_id) REFERENCES employes(id_employe),
            CHECK (probability_initial BETWEEN 1 AND 5),
            CHECK (severity_initial BETWEEN 1 AND 5),
            CHECK (probability_residual BETWEEN 1 AND 5),
            CHECK (severity_residual BETWEEN 1 AND 5),
            CHECK (level_initial IN ('low', 'medium', 'high', 'critical')),
            CHECK (level_residual IN ('low', 'medium', 'high', 'critical')),
            CHECK (hierarchy_control IN ('elimination', 'substitution', 'engineering', 'administrative', 'ppe')),
            CHECK (status IN ('open', 'in_progress', 'controlled', 'closed'))
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
        CREATE INDEX IF NOT EXISTS idx_equipment_maintenance_status_date
        ON equipment_maintenance(status, planned_date, priority)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_equipment_maintenance_site_date
        ON equipment_maintenance(site_id, planned_date)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_action_tracker_status_due
        ON action_tracker(status, due_date, priority)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_action_tracker_owner_due
        ON action_tracker(owner_employee_id, due_date)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_risk_assessments_level_status
        ON risk_assessments(level_initial, level_residual, status)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_risk_assessments_site_review
        ON risk_assessments(site_id, review_date)
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
        UPDATE training_types
        SET department_id = (SELECT id_department FROM training_departments WHERE nom = 'HSE'),
            updated_at = CURRENT_TIMESTAMP
        WHERE department_id IS NULL
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
    _ensure_default_role_permissions(connection)
    connection.execute("PRAGMA optimize")


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


def _rebuild_equipment_maintenance_type_check_if_needed(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'equipment_maintenance'"
    ).fetchone()
    sql = row["sql"] or "" if row else ""
    if not row or "'oil_change'" in sql:
        return

    connection.execute("ALTER TABLE equipment_maintenance RENAME TO equipment_maintenance_old")
    connection.execute(
        """
        CREATE TABLE equipment_maintenance (
            id_maintenance INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_code TEXT,
            equipment_name TEXT NOT NULL,
            category TEXT,
            site_id INTEGER,
            responsible_employee_id INTEGER,
            maintenance_type TEXT NOT NULL DEFAULT 'preventive',
            priority TEXT NOT NULL DEFAULT 'moyenne',
            status TEXT NOT NULL DEFAULT 'planifiee',
            planned_date TEXT NOT NULL,
            completed_date TEXT,
            next_due_date TEXT,
            current_odometer REAL,
            last_service_odometer REAL,
            service_interval_km REAL,
            next_due_odometer REAL,
            cost REAL NOT NULL DEFAULT 0,
            observations TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (site_id) REFERENCES sites(id_site),
            FOREIGN KEY (responsible_employee_id) REFERENCES employes(id_employe),
            CHECK (maintenance_type IN ('preventive', 'corrective', 'inspection', 'calibration', 'oil_change')),
            CHECK (priority IN ('basse', 'moyenne', 'haute', 'critique')),
            CHECK (status IN ('planifiee', 'en_cours', 'terminee', 'annulee', 'en_retard')),
            CHECK (completed_date IS NULL OR completed_date >= planned_date)
        )
        """
    )
    connection.execute(
        """
        INSERT INTO equipment_maintenance (
            id_maintenance, equipment_code, equipment_name, category, site_id,
            responsible_employee_id, maintenance_type, priority, status,
            planned_date, completed_date, next_due_date, current_odometer,
            last_service_odometer, service_interval_km, next_due_odometer,
            cost, observations, created_at, updated_at
        )
        SELECT
            id_maintenance, equipment_code, equipment_name, category, site_id,
            responsible_employee_id, maintenance_type, priority, status,
            planned_date, completed_date, next_due_date, current_odometer,
            last_service_odometer, service_interval_km, next_due_odometer,
            cost, observations, created_at, updated_at
        FROM equipment_maintenance_old
        """
    )
    connection.execute("DROP TABLE equipment_maintenance_old")


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


def _ensure_performance_indexes(connection: sqlite3.Connection) -> None:
    indexes = [
        """
        CREATE INDEX IF NOT EXISTS idx_employes_statut_type_site
        ON employes(statut, type_employe, site_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_employes_fonction
        ON employes(fonction_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_badges_employe
        ON badges(employe_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_badges_expiration
        ON badges(date_expiration)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_presences_date_employe
        ON presences(date_presence, employe_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_presences_employee_date_status
        ON presences(employe_id, date_presence, statut_presence)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_presences_statut_date
        ON presences(statut_presence, date_presence)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_employee_breaks_dates_status
        ON employee_breaks(date_debut, date_fin, statut)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_employee_breaks_type_employee_fin
        ON employee_breaks(type_break, employe_id, statut, date_fin)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_employee_breaks_employee_status_range
        ON employee_breaks(employe_id, statut, date_debut, date_fin)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_employee_breaks_status_employee_dates
        ON employee_breaks(statut, employe_id, date_debut, date_fin)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_timesheet_day_overrides_employee_date
        ON timesheet_day_overrides(employe_id, date_presence)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_timesheet_day_settings_date
        ON timesheet_day_settings(date_presence)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_formations_type_expiration
        ON formations(type_training_id, date_expiration)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_training_types_department
        ON training_types(department_id, actif)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_toolbox_theme_catalog_active_required
        ON toolbox_theme_catalog(actif, obligatoire, theme)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_themes_securite_site_date
        ON themes_securite(site_id, date_theme)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_epi_type_etat
        ON epi(type_epi_id, etat, actif)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_stock_epi_epi
        ON stock_epi(epi_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_mouvements_stock_epi_date
        ON mouvements_stock_epi(epi_id, date_mouvement)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_affectations_epi_active_employee
        ON affectations_epi(employe_id, date_retour)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_utilisateurs_role_status
        ON utilisateurs(role_id, statut)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_role_module_permissions_module
        ON role_module_permissions(module_key)
        """,
    ]
    for statement in indexes:
        connection.execute(statement)


def _ensure_default_role_permissions(connection: sqlite3.Connection) -> None:
    role_modules = {
        "Administrateur": [
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
        ],
        "Officier HSE": ["Dashboard", "TrainingManagement", "ToolboxTalk", "MaintenanceActions", "Alerts", "AiAssistant"],
        "Superviseur": ["Dashboard", "EmployeeManagement", "ToolboxTalk", "TimeSheet", "MonthlyTimesheet", "MaintenanceActions", "Alerts"],
        "Responsable stock": ["Dashboard", "Ppe", "MaintenanceActions", "Alerts"],
        "Direction": ["Dashboard", "MaintenanceActions", "Alerts", "AiAssistant"],
    }
    for role_name, modules in role_modules.items():
        role = connection.execute(
            "SELECT id_role FROM roles WHERE nom = ?",
            (role_name,),
        ).fetchone()
        if role is None:
            continue
        existing = connection.execute(
            "SELECT COUNT(*) AS total FROM role_module_permissions WHERE role_id = ?",
            (role["id_role"],),
        ).fetchone()
        if role_name != "Administrateur" and int(existing["total"] or 0):
            continue
        for module in modules:
            connection.execute(
                """
                INSERT OR IGNORE INTO role_module_permissions(role_id, module_key)
                VALUES (?, ?)
                """,
                (role["id_role"], module),
            )
