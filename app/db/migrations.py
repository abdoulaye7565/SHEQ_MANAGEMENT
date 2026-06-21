from __future__ import annotations

import sqlite3

from app.config import ROLE_MODULES


def run_lightweight_migrations(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            id         INTEGER PRIMARY KEY CHECK (id = 1),
            version    INTEGER NOT NULL DEFAULT 0,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    connection.execute(
        "INSERT OR IGNORE INTO schema_version (id, version) VALUES (1, 0)"
    )
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
    _ddl_changes = sum([
        _add_column_if_missing(connection, "sites", "department_id", "INTEGER"),
        _add_column_if_missing(connection, "employes", "nom", "TEXT"),
        _add_column_if_missing(connection, "employes", "prenom", "TEXT"),
        _add_column_if_missing(connection, "employes", "departure_type", "TEXT"),
        _add_column_if_missing(connection, "employes", "departure_date", "TEXT"),
        _add_column_if_missing(connection, "employes", "departure_comment", "TEXT"),
        _add_column_if_missing(connection, "timesheet_day_settings", "day_type", "TEXT NOT NULL DEFAULT 'work'"),
        _add_column_if_missing(connection, "badges", "date_expiration", "TEXT"),
        _add_column_if_missing(connection, "training_types", "department_id", "INTEGER"),
        _add_column_if_missing(connection, "presences", "statut_presence", "TEXT NOT NULL DEFAULT 'absent'"),
        _add_column_if_missing(connection, "formations", "structure_responsable", "TEXT"),
        _add_column_if_missing(connection, "equipment_maintenance", "current_odometer", "REAL"),
        _add_column_if_missing(connection, "equipment_maintenance", "last_service_odometer", "REAL"),
        _add_column_if_missing(connection, "equipment_maintenance", "service_interval_km", "REAL"),
        _add_column_if_missing(connection, "equipment_maintenance", "next_due_odometer", "REAL"),
        _add_column_if_missing(connection, "mobile_sync_devices", "mobile_role", "TEXT NOT NULL DEFAULT 'hse'"),
        _add_column_if_missing(connection, "mobile_sync_events", "operator_username", "TEXT"),
        _add_column_if_missing(connection, "toolbox_theme_catalog", "code_theme", "TEXT"),
        _add_column_if_missing(connection, "toolbox_theme_catalog", "category", "TEXT NOT NULL DEFAULT 'HSE General'"),
        _add_column_if_missing(connection, "toolbox_theme_catalog", "risk_level", "TEXT NOT NULL DEFAULT 'moyen'"),
        _add_column_if_missing(connection, "toolbox_theme_catalog", "topic_en", "TEXT"),
        _add_column_if_missing(connection, "toolbox_theme_catalog", "theme_fr", "TEXT"),
        _add_column_if_missing(connection, "toolbox_theme_catalog", "frequency", "TEXT NOT NULL DEFAULT 'mensuelle'"),
        _add_column_if_missing(connection, "toolbox_theme_catalog", "site_id", "INTEGER"),
        _add_column_if_missing(connection, "toolbox_theme_catalog", "department_id", "INTEGER"),
        _add_column_if_missing(connection, "toolbox_theme_catalog", "status", "TEXT NOT NULL DEFAULT 'actif'"),
        _add_column_if_missing(connection, "toolbox_theme_catalog", "last_used_at", "TEXT"),
        _add_column_if_missing(connection, "toolbox_theme_catalog", "usage_count", "INTEGER NOT NULL DEFAULT 0"),
        _add_column_if_missing(connection, "toolbox_theme_catalog", "average_effectiveness", "REAL NOT NULL DEFAULT 0"),
    ])
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS mobile_user_sessions (
            id_session INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            last_used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES mobile_sync_devices(device_id),
            FOREIGN KEY (user_id) REFERENCES utilisateurs(id_user)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_mobile_user_sessions_device
        ON mobile_user_sessions(device_id, expires_at)
        """
    )
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
        CREATE TABLE IF NOT EXISTS maintenance_parts (
            id_part INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT,
            quantity_available INTEGER NOT NULL DEFAULT 0,
            minimum_threshold INTEGER NOT NULL DEFAULT 0,
            unit_cost REAL NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (quantity_available >= 0),
            CHECK (minimum_threshold >= 0),
            CHECK (unit_cost >= 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS maintenance_inspections (
            id_inspection INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_code TEXT,
            equipment_name TEXT NOT NULL,
            inspection_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ok',
            next_inspection_date TEXT,
            inspector TEXT,
            observations TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (status IN ('ok', 'a_surveiller', 'critique', 'hors_service'))
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
        CREATE TABLE IF NOT EXISTS toolbox_campaigns (
            id_campaign INTEGER PRIMARY KEY AUTOINCREMENT,
            code_campaign TEXT UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            site_id INTEGER,
            department_id INTEGER,
            status TEXT NOT NULL DEFAULT 'planifiee',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (site_id) REFERENCES sites(id_site),
            FOREIGN KEY (department_id) REFERENCES departments(id_department)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS toolbox_campaign_themes (
            id_campaign_theme INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            topic_id INTEGER NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES toolbox_campaigns(id_campaign),
            FOREIGN KEY (topic_id) REFERENCES toolbox_theme_catalog(id_topic),
            UNIQUE (campaign_id, topic_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS toolbox_theme_usage (
            id_usage INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER,
            theme_id INTEGER,
            usage_date TEXT NOT NULL,
            site_id INTEGER,
            department_id INTEGER,
            facilitator TEXT,
            participants_count INTEGER NOT NULL DEFAULT 0,
            comprehension_score REAL,
            observation TEXT,
            source TEXT NOT NULL DEFAULT 'planning',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (topic_id) REFERENCES toolbox_theme_catalog(id_topic),
            FOREIGN KEY (theme_id) REFERENCES themes_securite(id_theme),
            FOREIGN KEY (site_id) REFERENCES sites(id_site),
            FOREIGN KEY (department_id) REFERENCES departments(id_department),
            UNIQUE (usage_date, topic_id, site_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS toolbox_effectiveness_evaluations (
            id_evaluation INTEGER PRIMARY KEY AUTOINCREMENT,
            usage_id INTEGER NOT NULL,
            participation_rate REAL NOT NULL DEFAULT 0,
            comprehension_score REAL NOT NULL DEFAULT 0,
            facilitator_rating REAL NOT NULL DEFAULT 0,
            session_quality REAL NOT NULL DEFAULT 0,
            global_score REAL NOT NULL DEFAULT 0,
            comments TEXT,
            evaluated_by TEXT,
            evaluated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usage_id) REFERENCES toolbox_theme_usage(id_usage),
            UNIQUE (usage_id)
        )
        """
    )
    _migrate_toolbox_theme_bank_data(connection)
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
        WHERE validite_mois IS NULL OR validite_mois = 0
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
        CREATE TABLE IF NOT EXISTS mobile_sync_devices (
            device_id TEXT PRIMARY KEY,
            device_name TEXT,
            last_seen_at TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (status IN ('active', 'blocked'))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS mobile_sync_events (
            id_event INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload_hash TEXT,
            records_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'received',
            message TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES mobile_sync_devices(device_id),
            CHECK (status IN ('received', 'applied', 'rejected', 'error'))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS mobile_toolbox_confirmations (
            id_confirmation INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            date_theme TEXT NOT NULL,
            theme TEXT,
            facilitator TEXT,
            site_id INTEGER,
            attendees_count INTEGER NOT NULL DEFAULT 0,
            comments TEXT,
            synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES mobile_sync_devices(device_id),
            FOREIGN KEY (site_id) REFERENCES sites(id_site)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS mobile_maintenance_observations (
            id_observation INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            observation_date TEXT NOT NULL,
            equipment_label TEXT NOT NULL,
            site_id INTEGER,
            priority TEXT NOT NULL DEFAULT 'moyenne',
            observation TEXT NOT NULL,
            action_id INTEGER,
            synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES mobile_sync_devices(device_id),
            FOREIGN KEY (site_id) REFERENCES sites(id_site),
            FOREIGN KEY (action_id) REFERENCES action_tracker(id_action),
            CHECK (priority IN ('basse', 'moyenne', 'haute', 'critique'))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS mobile_ppe_checks (
            id_check        INTEGER PRIMARY KEY AUTOINCREMENT,
            check_date      TEXT NOT NULL,
            employe_name    TEXT,
            employe_id      INTEGER,
            resultats_json  TEXT,
            statut_global   TEXT NOT NULL DEFAULT 'conforme',
            observations    TEXT,
            synced_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employe_id) REFERENCES employes(id_employe),
            CHECK (statut_global IN ('conforme', 'non_conforme'))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS mobile_field_observations (
            id_observation  INTEGER PRIMARY KEY AUTOINCREMENT,
            obs_date        TEXT NOT NULL,
            lieu            TEXT,
            type_obs        TEXT NOT NULL DEFAULT 'condition_unsafe',
            description     TEXT NOT NULL,
            priorite        TEXT NOT NULL DEFAULT 'moyenne',
            action_requise  INTEGER NOT NULL DEFAULT 0,
            notes           TEXT,
            synced_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (type_obs IN ('acte_unsafe', 'condition_unsafe', 'bonne_pratique', 'presqu_accident')),
            CHECK (priorite IN ('faible', 'moyenne', 'elevee', 'critique'))
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
        CREATE INDEX IF NOT EXISTS idx_mobile_sync_events_device_date
        ON mobile_sync_events(device_id, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_mobile_toolbox_confirmations_date
        ON mobile_toolbox_confirmations(date_theme, site_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_mobile_maintenance_observations_date
        ON mobile_maintenance_observations(observation_date, site_id)
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
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_register (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            activity TEXT,
            location TEXT,
            zone TEXT,
            hazard_type TEXT NOT NULL DEFAULT 'physique',
            affected_people TEXT,
            source_of_danger TEXT,
            probability INTEGER NOT NULL DEFAULT 1,
            severity INTEGER NOT NULL DEFAULT 1,
            risk_score INTEGER NOT NULL DEFAULT 1,
            risk_level TEXT NOT NULL DEFAULT 'faible',
            existing_controls TEXT,
            residual_probability INTEGER DEFAULT 1,
            residual_severity INTEGER DEFAULT 1,
            residual_score INTEGER DEFAULT 1,
            residual_level TEXT DEFAULT 'faible',
            status TEXT NOT NULL DEFAULT 'ouvert',
            owner TEXT,
            review_date TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_controls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            risk_id INTEGER NOT NULL,
            control_type TEXT NOT NULL DEFAULT 'administratif',
            description TEXT NOT NULL,
            responsible TEXT,
            target_date TEXT,
            status TEXT NOT NULL DEFAULT 'planifie',
            effectiveness TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (risk_id) REFERENCES risk_register(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            risk_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            changed_by TEXT,
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            risk_id INTEGER NOT NULL,
            link_type TEXT NOT NULL,
            linked_id INTEGER,
            linked_label TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (risk_id) REFERENCES risk_register(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS accidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL,
            type_evenement TEXT NOT NULL DEFAULT 'presquaccident',
            date_evenement TEXT NOT NULL,
            heure_evenement TEXT,
            lieu TEXT,
            zone TEXT,
            description TEXT NOT NULL,
            employe_id INTEGER,
            tiers_implique TEXT,
            gravite TEXT NOT NULL DEFAULT 'benin',
            jours_arret INTEGER DEFAULT 0,
            statut TEXT NOT NULL DEFAULT 'ouvert',
            created_by TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (employe_id) REFERENCES employes(id_employe)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS causes_accidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accident_id INTEGER NOT NULL,
            type_cause TEXT NOT NULL DEFAULT 'immediate',
            description TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (accident_id) REFERENCES accidents(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS actions_accident (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accident_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            responsable TEXT,
            date_echeance TEXT,
            statut TEXT NOT NULL DEFAULT 'planifie',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (accident_id) REFERENCES accidents(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS permis_travail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL,
            type_permis TEXT NOT NULL DEFAULT 'general',
            titre TEXT NOT NULL,
            lieu TEXT,
            zone TEXT,
            date_emission TEXT NOT NULL,
            date_debut TEXT NOT NULL,
            date_fin TEXT NOT NULL,
            heure_debut TEXT,
            heure_fin TEXT,
            description_travaux TEXT,
            effectif INTEGER DEFAULT 1,
            entreprise TEXT,
            responsable_travaux TEXT,
            risques TEXT,
            precautions TEXT,
            equipements_requis TEXT,
            statut TEXT NOT NULL DEFAULT 'brouillon',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS validations_permis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            permis_id INTEGER NOT NULL,
            role_validateur TEXT NOT NULL,
            nom_validateur TEXT,
            statut TEXT NOT NULL DEFAULT 'en_attente',
            commentaire TEXT,
            date_validation TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (permis_id) REFERENCES permis_travail(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications_qhse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL DEFAULT 'general',
            source_id TEXT,
            priorite TEXT NOT NULL DEFAULT 'info',
            titre TEXT NOT NULL,
            message TEXT,
            statut TEXT NOT NULL DEFAULT 'nouveau',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            acknowledged_at TEXT,
            acknowledged_by TEXT
        )
        """
    )
    if _ddl_changes:
        _row = connection.execute("SELECT version FROM schema_version WHERE id=1").fetchone()
        connection.execute(
            "UPDATE schema_version SET version=?, applied_at=datetime('now') WHERE id=1",
            (int(_row["version"]) + 1,),
        )
    connection.execute("PRAGMA optimize")


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> bool:
    """Return True if the column was added, False if it already existed."""
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        return True
    return False


def _migrate_toolbox_theme_bank_data(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO toolbox_theme_catalog(theme, obligatoire, actif)
        SELECT DISTINCT TRIM(theme), 0, 1
        FROM themes_securite
        WHERE COALESCE(TRIM(theme), '') <> ''
        """
    )
    connection.execute(
        """
        UPDATE toolbox_theme_catalog
        SET code_theme = printf('TBX-%03d', id_topic)
        WHERE COALESCE(code_theme, '') = ''
        """
    )
    connection.execute(
        """
        UPDATE toolbox_theme_catalog
        SET topic_en = CASE
                WHEN instr(theme, ' / ') > 0 THEN TRIM(substr(theme, 1, instr(theme, ' / ') - 1))
                ELSE theme
            END,
            theme_fr = CASE
                WHEN instr(theme, ' / ') > 0 THEN TRIM(substr(theme, instr(theme, ' / ') + 3))
                ELSE theme
            END
        WHERE COALESCE(topic_en, '') = ''
           OR COALESCE(theme_fr, '') = ''
        """
    )
    connection.execute(
        """
        UPDATE toolbox_theme_catalog
        SET status = CASE WHEN actif = 1 THEN 'actif' ELSE 'inactif' END
        WHERE COALESCE(status, '') = ''
           OR status NOT IN ('actif', 'en_attente', 'inactif', 'obsolete')
        """
    )
    connection.execute(
        """
        UPDATE toolbox_theme_catalog
        SET usage_count = (
                SELECT COUNT(*)
                FROM themes_securite ts
                WHERE TRIM(ts.theme) = TRIM(toolbox_theme_catalog.theme)
            ),
            last_used_at = (
                SELECT MAX(ts.date_theme)
                FROM themes_securite ts
                WHERE TRIM(ts.theme) = TRIM(toolbox_theme_catalog.theme)
            )
        """
    )
    connection.execute(
        """
        INSERT INTO toolbox_theme_usage (
            topic_id, theme_id, usage_date, site_id, department_id,
            facilitator, participants_count, observation, source
        )
        SELECT
            catalog.id_topic,
            ts.id_theme,
            ts.date_theme,
            ts.site_id,
            sites.department_id,
            ts.facilitateur,
            COALESCE(confirmations.attendees_count, 0),
            confirmations.comments,
            CASE WHEN confirmations.id_confirmation IS NULL THEN 'planning' ELSE 'mobile_confirmation' END
        FROM themes_securite ts
        JOIN toolbox_theme_catalog catalog ON TRIM(catalog.theme) = TRIM(ts.theme)
        LEFT JOIN sites ON sites.id_site = ts.site_id
        LEFT JOIN mobile_toolbox_confirmations confirmations
          ON confirmations.date_theme = ts.date_theme
         AND (confirmations.site_id = ts.site_id OR confirmations.site_id IS NULL OR ts.site_id IS NULL)
        WHERE COALESCE(TRIM(ts.theme), '') <> ''
          AND NOT EXISTS (
              SELECT 1
              FROM toolbox_theme_usage usage
              WHERE usage.theme_id = ts.id_theme
          )
        """
    )


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
        CREATE UNIQUE INDEX IF NOT EXISTS idx_toolbox_theme_catalog_code
        ON toolbox_theme_catalog(code_theme)
        WHERE code_theme IS NOT NULL
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_toolbox_theme_catalog_professional_filters
        ON toolbox_theme_catalog(status, category, risk_level, frequency, site_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_toolbox_theme_usage_topic_date
        ON toolbox_theme_usage(topic_id, usage_date)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_toolbox_campaigns_period_status
        ON toolbox_campaigns(start_date, end_date, status)
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
    for role_name, modules in ROLE_MODULES.items():
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
