PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sites (
    id_site INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    localisation TEXT,
    department_id INTEGER,
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (department_id) REFERENCES departments(id_department)
);

CREATE TABLE IF NOT EXISTS departments (
    id_department INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    description TEXT,
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS groupes (
    id_groupe INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    nom TEXT NOT NULL,
    shift_defaut TEXT,
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (site_id) REFERENCES sites(id_site),
    UNIQUE (site_id, nom)
);

CREATE TABLE IF NOT EXISTS fonctions (
    id_fonction INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    description TEXT,
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS shifts (
    id_shift INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    libelle TEXT NOT NULL,
    CHECK (code IN ('DAY', 'NIGHT', 'BREAK'))
);

CREATE TABLE IF NOT EXISTS break_types (
    id_break_type INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    libelle TEXT NOT NULL,
    CHECK (code IN ('NORMAL', 'SICK', 'PERMISSION'))
);

CREATE TABLE IF NOT EXISTS training_types (
    id_training_type INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    categorie TEXT,
    validite_mois INTEGER NOT NULL DEFAULT 24,
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS training_departments (
    id_department INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS types_epi (
    id_type_epi INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    description TEXT,
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS roles (
    id_role INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS utilisateurs (
    id_user INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    statut TEXT NOT NULL DEFAULT 'actif',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (role_id) REFERENCES roles(id_role)
);

CREATE TABLE IF NOT EXISTS role_module_permissions (
    role_id INTEGER NOT NULL,
    module_key TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, module_key),
    FOREIGN KEY (role_id) REFERENCES roles(id_role)
);

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
);

CREATE TABLE IF NOT EXISTS employes (
    id_employe INTEGER PRIMARY KEY AUTOINCREMENT,
    matricule TEXT UNIQUE,
    nom TEXT,
    prenom TEXT,
    nom_complet TEXT NOT NULL,
    fonction_id INTEGER NOT NULL,
    site_id INTEGER NOT NULL,
    groupe_id INTEGER,
    shift_id INTEGER NOT NULL,
    type_employe TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'actif',
    departure_type TEXT,
    departure_date TEXT,
    departure_comment TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (fonction_id) REFERENCES fonctions(id_fonction),
    FOREIGN KEY (site_id) REFERENCES sites(id_site),
    FOREIGN KEY (groupe_id) REFERENCES groupes(id_groupe),
    FOREIGN KEY (shift_id) REFERENCES shifts(id_shift),
    CHECK (type_employe IN ('national', 'expatriate')),
    CHECK (departure_type IS NULL OR departure_type IN ('licencie', 'demissionne', 'autre'))
);

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
);

CREATE TABLE IF NOT EXISTS badges (
    id_badge INTEGER PRIMARY KEY AUTOINCREMENT,
    employe_id INTEGER NOT NULL UNIQUE,
    numero_badge TEXT NOT NULL UNIQUE,
    statut TEXT NOT NULL DEFAULT 'valide',
    date_remise TEXT,
    date_expiration TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (employe_id) REFERENCES employes(id_employe)
);

CREATE TABLE IF NOT EXISTS formations (
    id_formation INTEGER PRIMARY KEY AUTOINCREMENT,
    employe_id INTEGER NOT NULL,
    type_training_id INTEGER NOT NULL,
    date_debut TEXT NOT NULL,
    date_expiration TEXT NOT NULL,
    facilitateur TEXT,
    structure_responsable TEXT,
    statut TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (employe_id) REFERENCES employes(id_employe),
    FOREIGN KEY (type_training_id) REFERENCES training_types(id_training_type)
);

CREATE TABLE IF NOT EXISTS presences (
    id_presence INTEGER PRIMARY KEY AUTOINCREMENT,
    employe_id INTEGER NOT NULL,
    date_presence TEXT NOT NULL,
    statut_presence TEXT NOT NULL DEFAULT 'absent',
    heure_entree TEXT,
    heure_sortie TEXT,
    heures_travaillees REAL NOT NULL DEFAULT 0,
    shift_id INTEGER NOT NULL,
    break_type_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (employe_id) REFERENCES employes(id_employe),
    FOREIGN KEY (shift_id) REFERENCES shifts(id_shift),
    FOREIGN KEY (break_type_id) REFERENCES break_types(id_break_type),
    CHECK (statut_presence IN ('present', 'absent')),
    UNIQUE (employe_id, date_presence)
);

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
);

CREATE INDEX IF NOT EXISTS idx_employee_breaks_employe_dates
    ON employee_breaks(employe_id, date_debut, date_fin);

CREATE TABLE IF NOT EXISTS themes_securite (
    id_theme INTEGER PRIMARY KEY AUTOINCREMENT,
    date_theme TEXT NOT NULL,
    theme TEXT NOT NULL,
    facilitateur TEXT,
    site_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (site_id) REFERENCES sites(id_site)
);

CREATE TABLE IF NOT EXISTS toolbox_theme_catalog (
    id_topic INTEGER PRIMARY KEY AUTOINCREMENT,
    theme TEXT NOT NULL UNIQUE,
    obligatoire INTEGER NOT NULL DEFAULT 0,
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

DELETE FROM themes_securite
WHERE id_theme IN (
    SELECT old.id_theme
    FROM themes_securite old
    JOIN themes_securite keep
      ON keep.date_theme = old.date_theme
     AND keep.id_theme > old.id_theme
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_themes_securite_date
    ON themes_securite(date_theme);

CREATE TABLE IF NOT EXISTS epi (
    id_epi INTEGER PRIMARY KEY AUTOINCREMENT,
    type_epi_id INTEGER NOT NULL,
    nom TEXT NOT NULL,
    taille TEXT,
    norme TEXT,
    marque TEXT,
    modele TEXT,
    etat TEXT NOT NULL DEFAULT 'neuf',
    date_expiration TEXT,
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (type_epi_id) REFERENCES types_epi(id_type_epi)
);

CREATE TABLE IF NOT EXISTS stock_epi (
    id_stock INTEGER PRIMARY KEY AUTOINCREMENT,
    epi_id INTEGER NOT NULL UNIQUE,
    quantite_disponible INTEGER NOT NULL DEFAULT 0,
    seuil_minimum INTEGER NOT NULL DEFAULT 0,
    date_mise_a_jour TEXT,
    FOREIGN KEY (epi_id) REFERENCES epi(id_epi)
);

CREATE TABLE IF NOT EXISTS mouvements_stock_epi (
    id_mouvement INTEGER PRIMARY KEY AUTOINCREMENT,
    epi_id INTEGER NOT NULL,
    type_mouvement TEXT NOT NULL,
    quantite INTEGER NOT NULL,
    date_mouvement TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    motif TEXT,
    reference TEXT,
    FOREIGN KEY (epi_id) REFERENCES epi(id_epi),
    CHECK (type_mouvement IN ('entree', 'sortie', 'ajustement'))
);

CREATE TABLE IF NOT EXISTS affectations_epi (
    id_affectation INTEGER PRIMARY KEY AUTOINCREMENT,
    employe_id INTEGER NOT NULL,
    epi_id INTEGER NOT NULL,
    quantite INTEGER NOT NULL DEFAULT 1,
    date_remise TEXT NOT NULL,
    date_retour TEXT,
    statut TEXT NOT NULL DEFAULT 'en_service',
    observations TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (employe_id) REFERENCES employes(id_employe),
    FOREIGN KEY (epi_id) REFERENCES epi(id_epi)
);

CREATE TABLE IF NOT EXISTS epi_requis_fonction (
    id_requis INTEGER PRIMARY KEY AUTOINCREMENT,
    fonction_id INTEGER NOT NULL,
    type_epi_id INTEGER NOT NULL,
    quantite INTEGER NOT NULL DEFAULT 1,
    obligatoire INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (fonction_id) REFERENCES fonctions(id_fonction),
    FOREIGN KEY (type_epi_id) REFERENCES types_epi(id_type_epi),
    UNIQUE (fonction_id, type_epi_id)
);

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
);

CREATE TABLE IF NOT EXISTS formations_requises_fonction (
    id_requis INTEGER PRIMARY KEY AUTOINCREMENT,
    fonction_id INTEGER NOT NULL,
    type_training_id INTEGER NOT NULL,
    obligatoire INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (fonction_id) REFERENCES fonctions(id_fonction),
    FOREIGN KEY (type_training_id) REFERENCES training_types(id_training_type),
    UNIQUE (fonction_id, type_training_id)
);

CREATE TABLE IF NOT EXISTS historique_shifts (
    id_historique INTEGER PRIMARY KEY AUTOINCREMENT,
    employe_id INTEGER NOT NULL,
    shift_id INTEGER NOT NULL,
    break_type_id INTEGER,
    date_debut TEXT NOT NULL,
    date_fin TEXT,
    commentaire TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employe_id) REFERENCES employes(id_employe),
    FOREIGN KEY (shift_id) REFERENCES shifts(id_shift),
    FOREIGN KEY (break_type_id) REFERENCES break_types(id_break_type)
);

CREATE TABLE IF NOT EXISTS alertes (
    id_alerte INTEGER PRIMARY KEY AUTOINCREMENT,
    type_alerte TEXT NOT NULL,
    reference_id INTEGER,
    message TEXT NOT NULL,
    niveau TEXT NOT NULL DEFAULT 'moyen',
    date_creation TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    statut TEXT NOT NULL DEFAULT 'ouverte',
    CHECK (niveau IN ('bas', 'moyen', 'haut', 'critique')),
    CHECK (statut IN ('ouverte', 'traitee', 'ignoree'))
);

CREATE INDEX IF NOT EXISTS idx_formations_employe_expiration
    ON formations(employe_id, date_expiration);

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
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_formations_unique_employee_type
    ON formations(employe_id, type_training_id);

CREATE INDEX IF NOT EXISTS idx_presences_employe_date
    ON presences(employe_id, date_presence);

CREATE TABLE IF NOT EXISTS attendance_day_locks (
    date_presence TEXT PRIMARY KEY,
    locked_by TEXT NOT NULL DEFAULT 'system',
    locked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    commentaire TEXT
);

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
);

CREATE TABLE IF NOT EXISTS timesheet_day_settings (
    date_presence TEXT PRIMARY KEY,
    has_drilling INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    commentaire TEXT
);

CREATE TABLE IF NOT EXISTS timesheet_day_overrides (
    employe_id INTEGER NOT NULL,
    date_presence TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    commentaire TEXT,
    PRIMARY KEY (employe_id, date_presence),
    FOREIGN KEY (employe_id) REFERENCES employes(id_employe),
    CHECK (status IN ('rest', 'absent'))
);

CREATE TABLE IF NOT EXISTS timesheet_month_locks (
    month TEXT PRIMARY KEY,
    locked_by TEXT NOT NULL DEFAULT 'system',
    locked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    commentaire TEXT
);

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
);

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
);

CREATE INDEX IF NOT EXISTS idx_attendance_audit_date
    ON attendance_audit(date_presence, employe_id);

CREATE INDEX IF NOT EXISTS idx_timesheet_audit_month
    ON timesheet_audit(month, date_presence, employe_id);

CREATE INDEX IF NOT EXISTS idx_timesheet_day_overrides_date
    ON timesheet_day_overrides(date_presence, employe_id);

CREATE INDEX IF NOT EXISTS idx_affectations_epi_employe_date
    ON affectations_epi(employe_id, date_remise);

CREATE INDEX IF NOT EXISTS idx_epi_inspections_epi_date
    ON epi_inspections(epi_id, date_inspection);

CREATE INDEX IF NOT EXISTS idx_alertes_statut_niveau
    ON alertes(statut, niveau);

CREATE INDEX IF NOT EXISTS idx_admin_audit_changed_at
    ON admin_audit(changed_at, action);

CREATE INDEX IF NOT EXISTS idx_employee_site_assignments_employee_dates
    ON employee_site_assignments(employe_id, date_debut, date_fin);

CREATE INDEX IF NOT EXISTS idx_employee_site_assignments_site_dates
    ON employee_site_assignments(site_id, date_debut, date_fin);

INSERT OR IGNORE INTO shifts(code, libelle) VALUES
    ('DAY', 'Day Shift'),
    ('NIGHT', 'Night Shift'),
    ('BREAK', 'Break');

INSERT OR IGNORE INTO break_types(code, libelle) VALUES
    ('NORMAL', 'Break Normal'),
    ('SICK', 'Sick Break'),
    ('PERMISSION', 'Permission');

INSERT OR IGNORE INTO shift_templates(shift_code, libelle, heure_entree, heure_sortie, actif) VALUES
    ('DAY', 'Travaux drilling 06-18', '06:00', '18:00', 1),
    ('NIGHT', 'Sans drilling 06-14', '06:00', '14:00', 1),
    ('BREAK', 'Hors service', '00:00', '00:00', 1);

UPDATE shift_templates
SET libelle = 'Travaux drilling 06-18',
    heure_entree = '06:00',
    heure_sortie = '18:00',
    updated_at = CURRENT_TIMESTAMP
WHERE shift_code = 'DAY';

UPDATE shift_templates
SET libelle = 'Sans drilling 06-14',
    heure_entree = '06:00',
    heure_sortie = '14:00',
    updated_at = CURRENT_TIMESTAMP
WHERE shift_code = 'NIGHT';

INSERT OR IGNORE INTO roles(nom, description) VALUES
    ('Administrateur', 'Parametrage global et administration'),
    ('Officier HSE', 'Formations, conformite et alertes'),
    ('Superviseur', 'Presence, shifts et suivi terrain'),
    ('Responsable stock', 'EPI, stock et seuils'),
    ('Direction', 'Rapports et indicateurs');

INSERT OR IGNORE INTO departments(nom, description, actif) VALUES
    ('Geologie', 'Departement geologie et operations terrain', 1);

INSERT OR IGNORE INTO sites(nom, localisation, actif) VALUES
    ('OREZONE', 'Site principal', 1);

INSERT OR IGNORE INTO sites(nom, localisation, actif) VALUES
    ('SYAMA', 'Site par defaut - departement Geologie', 1);

INSERT OR IGNORE INTO fonctions(nom, description, actif) VALUES
    ('Officier HSE', 'Suivi HSE, formations et conformite terrain', 1),
    ('Superviseur terrain', 'Encadrement operationnel et suivi des shifts', 1),
    ('Responsable stock', 'Gestion des EPI, seuils et mouvements de stock', 1),
    ('Operateur', 'Personnel operationnel du site', 1);

INSERT OR IGNORE INTO training_types(nom, categorie, validite_mois, actif) VALUES
    ('Induction HSE', 'obligatoire', 24, 1),
    ('Travail en hauteur', 'specialisee', 24, 1),
    ('Premiers secours', 'specialisee', 24, 1),
    ('Conduite defensive', 'specialisee', 24, 1);

UPDATE training_types
SET validite_mois = 24,
    updated_at = CURRENT_TIMESTAMP
WHERE validite_mois <> 24;

UPDATE badges
SET date_expiration = DATE(date_remise, '+2 years'),
    updated_at = CURRENT_TIMESTAMP
WHERE date_remise IS NOT NULL
  AND date_remise <> ''
  AND (
      date_expiration IS NULL
      OR date_expiration = ''
      OR date_expiration <> DATE(date_remise, '+2 years')
  );

INSERT OR IGNORE INTO training_departments(nom, actif) VALUES
    ('HSE', 1),
    ('Ressources humaines', 1),
    ('Operations', 1),
    ('Maintenance', 1),
    ('Mine', 1),
    ('Administration', 1),
    ('Sous-traitant', 1),
    ('Externe', 1);

UPDATE types_epi SET nom = 'Safety Helmet', description = 'Head protection for mining and drilling areas' WHERE nom = 'Casque de securite';
UPDATE types_epi SET nom = 'Safety Glasses', description = 'Eye protection against dust and impacts' WHERE nom = 'Lunettes de securite';
UPDATE types_epi SET nom = 'Protective Gloves', description = 'Hand protection for drilling and handling' WHERE nom = 'Gants de protection';
UPDATE types_epi SET nom = 'Safety Boots', description = 'Foot protection for mining operations' WHERE nom = 'Chaussures de securite';
UPDATE types_epi SET nom = 'High Visibility Vest', description = 'Visibility on mine site and traffic areas' WHERE nom = 'Gilet haute visibilite';
UPDATE types_epi SET nom = 'Hearing Protection', description = 'Noise protection around rigs and machines' WHERE nom = 'Protection auditive';
UPDATE types_epi SET nom = 'Respiratory Protection', description = 'Dust and particle protection during drilling' WHERE nom = 'Protection respiratoire';
UPDATE types_epi SET nom = 'Protective Clothing', description = 'Body protection for field operations' WHERE nom = 'Vetement de protection';
UPDATE types_epi SET nom = 'Fall Protection', description = 'Harness and lanyard for exposed work' WHERE nom = 'Protection antichute';
UPDATE types_epi SET nom = 'Face Protection', description = 'Face shield against projections and impacts' WHERE nom = 'Protection visage';

INSERT OR IGNORE INTO types_epi(nom, description, actif) VALUES
    ('Safety Helmet', 'Head protection for mining and drilling areas', 1),
    ('Safety Glasses', 'Eye protection against dust and impacts', 1),
    ('Protective Gloves', 'Hand protection for drilling and handling', 1),
    ('Safety Boots', 'Foot protection for mining operations', 1),
    ('High Visibility Vest', 'Visibility on mine site and traffic areas', 1),
    ('Hearing Protection', 'Noise protection around rigs and machines', 1),
    ('Respiratory Protection', 'Dust and particle protection during drilling', 1),
    ('Protective Clothing', 'Body protection for field operations', 1),
    ('Fall Protection', 'Harness and lanyard for exposed work', 1),
    ('Face Protection', 'Face shield against projections and impacts', 1);

UPDATE epi SET nom = 'Mining Hard Hat with Chin Strap', taille = 'Adjustable', modele = 'Drilling standard'
WHERE nom = 'Casque minier avec jugulaire' AND marque = 'Standard mine';
UPDATE epi SET nom = 'Clear Impact Safety Glasses', taille = 'One size', modele = 'Drilling standard'
WHERE nom = 'Lunettes anti-impact transparentes' AND marque = 'Standard mine';
UPDATE epi SET nom = 'Anti-Vibration Drilling Gloves', taille = 'M/L/XL', modele = 'Drilling standard'
WHERE nom = 'Gants anti-vibration pour forage' AND marque = 'Standard mine';
UPDATE epi SET nom = 'S3 Anti-Slip Safety Boots', taille = '39-46', modele = 'Drilling standard'
WHERE nom = 'Bottes de securite S3 antiderapantes' AND marque = 'Standard mine';

DELETE FROM stock_epi
WHERE epi_id IN (
    SELECT e.id_epi
    FROM epi e
    WHERE e.marque = 'Standard mine'
      AND e.nom NOT IN (
          'Mining Hard Hat with Chin Strap',
          'Clear Impact Safety Glasses',
          'Anti-Vibration Drilling Gloves',
          'S3 Anti-Slip Safety Boots'
      )
      AND NOT EXISTS (SELECT 1 FROM affectations_epi ae WHERE ae.epi_id = e.id_epi)
);

DELETE FROM mouvements_stock_epi
WHERE epi_id IN (
    SELECT e.id_epi
    FROM epi e
    WHERE e.marque = 'Standard mine'
      AND e.nom NOT IN (
          'Mining Hard Hat with Chin Strap',
          'Clear Impact Safety Glasses',
          'Anti-Vibration Drilling Gloves',
          'S3 Anti-Slip Safety Boots'
      )
      AND NOT EXISTS (SELECT 1 FROM affectations_epi ae WHERE ae.epi_id = e.id_epi)
);

DELETE FROM epi
WHERE marque = 'Standard mine'
  AND nom NOT IN (
      'Mining Hard Hat with Chin Strap',
      'Clear Impact Safety Glasses',
      'Anti-Vibration Drilling Gloves',
      'S3 Anti-Slip Safety Boots'
  )
  AND NOT EXISTS (SELECT 1 FROM affectations_epi ae WHERE ae.epi_id = epi.id_epi);

UPDATE epi
SET actif = 0, updated_at = CURRENT_TIMESTAMP
WHERE marque = 'Standard mine'
  AND nom NOT IN (
      'Mining Hard Hat with Chin Strap',
      'Clear Impact Safety Glasses',
      'Anti-Vibration Drilling Gloves',
      'S3 Anti-Slip Safety Boots'
  );

INSERT INTO epi(type_epi_id, nom, taille, norme, marque, modele, etat, actif)
SELECT te.id_type_epi, seed.nom, seed.taille, seed.norme, 'Standard mine', 'Drilling standard', 'neuf', 1
FROM (
    SELECT 'Safety Helmet' AS type_nom, 'Mining Hard Hat with Chin Strap' AS nom, 'Adjustable' AS taille, 'EN 397 / ANSI Z89.1' AS norme
    UNION ALL SELECT 'Safety Glasses', 'Clear Impact Safety Glasses', 'One size', 'EN 166 / ANSI Z87.1'
    UNION ALL SELECT 'Protective Gloves', 'Anti-Vibration Drilling Gloves', 'M/L/XL', 'EN 388'
    UNION ALL SELECT 'Safety Boots', 'S3 Anti-Slip Safety Boots', '39-46', 'EN ISO 20345 S3'
) seed
JOIN types_epi te ON te.nom = seed.type_nom
WHERE NOT EXISTS (
    SELECT 1 FROM epi existing
    WHERE existing.nom = seed.nom
      AND existing.type_epi_id = te.id_type_epi
);

INSERT OR IGNORE INTO stock_epi(epi_id, quantite_disponible, seuil_minimum, date_mise_a_jour)
SELECT e.id_epi,
       CASE WHEN e.nom = 'Anti-Vibration Drilling Gloves' THEN 50 ELSE 20 END,
       CASE WHEN e.nom = 'Anti-Vibration Drilling Gloves' THEN 15 ELSE 5 END,
       CURRENT_TIMESTAMP
FROM epi e
WHERE e.marque = 'Standard mine'
  AND e.nom IN (
      'Mining Hard Hat with Chin Strap',
      'Clear Impact Safety Glasses',
      'Anti-Vibration Drilling Gloves',
      'S3 Anti-Slip Safety Boots'
  );
