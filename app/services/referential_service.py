from __future__ import annotations

import sqlite3
from typing import Any

from app.db.connection import db_session


REFERENTIAL_CONFIGS: dict[str, dict[str, Any]] = {
    "sites": {
        "label": "Sites",
        "table": "sites",
        "pk": "id_site",
        "display": "nom",
        "fields": [
            {"name": "nom", "label": "Nom du site", "type": "text", "required": True},
            {"name": "localisation", "label": "Localisation", "type": "text"},
            {
                "name": "department_id",
                "label": "Departement",
                "type": "fk",
                "ref_table": "departments",
                "ref_pk": "id_department",
                "ref_display": "nom",
            },
            {"name": "actif", "label": "Actif", "type": "bool", "default": 1},
        ],
    },
    "departments": {
        "label": "Departements",
        "table": "departments",
        "pk": "id_department",
        "display": "nom",
        "fields": [
            {"name": "nom", "label": "Nom du departement", "type": "text", "required": True},
            {"name": "description", "label": "Description", "type": "text"},
            {"name": "actif", "label": "Actif", "type": "bool", "default": 1},
        ],
    },
    "groupes": {
        "label": "Groupes",
        "table": "groupes",
        "pk": "id_groupe",
        "display": "nom",
        "fields": [
            {
                "name": "site_id",
                "label": "Site",
                "type": "fk",
                "required": True,
                "ref_table": "sites",
                "ref_pk": "id_site",
                "ref_display": "nom",
            },
            {"name": "nom", "label": "Nom du groupe", "type": "text", "required": True},
            {"name": "shift_defaut", "label": "Shift par defaut", "type": "text"},
            {"name": "actif", "label": "Actif", "type": "bool", "default": 1},
        ],
    },
    "fonctions": {
        "label": "Fonctions",
        "table": "fonctions",
        "pk": "id_fonction",
        "display": "nom",
        "fields": [
            {"name": "nom", "label": "Nom de la fonction", "type": "text", "required": True},
            {"name": "description", "label": "Description", "type": "text"},
            {"name": "actif", "label": "Actif", "type": "bool", "default": 1},
        ],
    },
    "training_types": {
        "label": "Types de formation",
        "table": "training_types",
        "pk": "id_training_type",
        "display": "nom",
        "fields": [
            {"name": "nom", "label": "Nom de la formation", "type": "text", "required": True},
            {"name": "categorie", "label": "Categorie", "type": "text"},
            {"name": "validite_mois", "label": "Validite en mois", "type": "int", "default": 24},
            {"name": "actif", "label": "Actif", "type": "bool", "default": 1},
        ],
    },
    "training_departments": {
        "label": "Departements formation",
        "table": "training_departments",
        "pk": "id_department",
        "display": "nom",
        "fields": [
            {"name": "nom", "label": "Nom du departement", "type": "text", "required": True},
            {"name": "actif", "label": "Actif", "type": "bool", "default": 1},
        ],
    },
    "types_epi": {
        "label": "Types EPI",
        "table": "types_epi",
        "pk": "id_type_epi",
        "display": "nom",
        "fields": [
            {"name": "nom", "label": "Nom du type EPI", "type": "text", "required": True},
            {"name": "description", "label": "Description", "type": "text"},
            {"name": "actif", "label": "Actif", "type": "bool", "default": 1},
        ],
    },
    "shifts": {
        "label": "Shifts",
        "table": "shifts",
        "pk": "id_shift",
        "display": "libelle",
        "fields": [
            {"name": "code", "label": "Code", "type": "choice", "required": True, "choices": ["DAY", "NIGHT", "BREAK"]},
            {"name": "libelle", "label": "Libelle", "type": "text", "required": True},
        ],
    },
    "shift_templates": {
        "label": "Horaires operations",
        "table": "shift_templates",
        "pk": "id_template",
        "display": "libelle",
        "fields": [
            {"name": "shift_code", "label": "Code", "type": "choice", "required": True, "choices": ["DAY", "NIGHT", "BREAK"]},
            {"name": "libelle", "label": "Libelle", "type": "text", "required": True},
            {"name": "heure_entree", "label": "Heure entree", "type": "text", "required": True},
            {"name": "heure_sortie", "label": "Heure sortie", "type": "text", "required": True},
            {"name": "actif", "label": "Actif", "type": "bool", "default": 1},
        ],
    },
    "break_types": {
        "label": "Types de break",
        "table": "break_types",
        "pk": "id_break_type",
        "display": "libelle",
        "fields": [
            {"name": "code", "label": "Code", "type": "choice", "required": True, "choices": ["NORMAL", "SICK", "PERMISSION"]},
            {"name": "libelle", "label": "Libelle", "type": "text", "required": True},
        ],
    },
    "roles": {
        "label": "Roles",
        "table": "roles",
        "pk": "id_role",
        "display": "nom",
        "fields": [
            {"name": "nom", "label": "Nom du role", "type": "text", "required": True},
            {"name": "description", "label": "Description", "type": "text"},
        ],
    },
}


def list_config_keys() -> list[str]:
    return list(REFERENTIAL_CONFIGS.keys())


def get_config(key: str) -> dict[str, Any]:
    try:
        return REFERENTIAL_CONFIGS[key]
    except KeyError as exc:
        raise ValueError(f"Referentiel inconnu: {key}") from exc


def list_referential_counts() -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []

    with db_session() as connection:
        for key in list_config_keys():
            config = get_config(key)
            table = config["table"]
            display = config["display"]
            total = connection.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
            preview_rows = connection.execute(
                f"SELECT {display} FROM {table} ORDER BY {display} LIMIT 3"
            ).fetchall()
            preview = ", ".join(str(row[display]) for row in preview_rows) or "-"
            rows.append(
                {
                    "key": key,
                    "label": config["label"],
                    "total": int(total["total"]),
                    "preview": preview,
                }
            )

    return rows


def list_records(key: str) -> list[dict[str, Any]]:
    config = get_config(key)
    columns = [config["pk"], *[field["name"] for field in config["fields"]]]
    order_column = config["display"]

    with db_session() as connection:
        rows = connection.execute(
            f"SELECT {', '.join(columns)} FROM {config['table']} ORDER BY {order_column}"
        ).fetchall()
        return [dict(row) for row in rows]


def get_foreign_key_options(key: str, field_name: str) -> list[dict[str, Any]]:
    field = _get_field(key, field_name)
    if field["type"] != "fk":
        raise ValueError(f"Champ non relationnel: {field_name}")

    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT {field['ref_pk']} AS value, {field['ref_display']} AS label
            FROM {field['ref_table']}
            ORDER BY {field['ref_display']}
            """
        ).fetchall()
        return [dict(row) for row in rows]


def create_record(key: str, values: dict[str, Any]) -> int:
    config = get_config(key)
    payload = _clean_values(config, values)
    _validate_payload(config, payload)

    columns = list(payload.keys())
    placeholders = ", ".join("?" for _ in columns)

    try:
        with db_session() as connection:
            cursor = connection.execute(
                f"INSERT INTO {config['table']} ({', '.join(columns)}) VALUES ({placeholders})",
                [payload[column] for column in columns],
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise ValueError(_friendly_integrity_error(exc)) from exc


def update_record(key: str, record_id: int, values: dict[str, Any]) -> None:
    config = get_config(key)
    payload = _clean_values(config, values)
    _validate_payload(config, payload)

    assignments = ", ".join(f"{column} = ?" for column in payload.keys())
    params = [payload[column] for column in payload.keys()]
    params.append(record_id)

    try:
        with db_session() as connection:
            connection.execute(
                f"UPDATE {config['table']} SET {assignments} WHERE {config['pk']} = ?",
                params,
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError(_friendly_integrity_error(exc)) from exc


def delete_record(key: str, record_id: int) -> None:
    config = get_config(key)

    try:
        with db_session() as connection:
            connection.execute(
                f"DELETE FROM {config['table']} WHERE {config['pk']} = ?",
                (record_id,),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError(
            "Suppression impossible: cet element est deja utilise dans un autre module."
        ) from exc


def _get_field(key: str, field_name: str) -> dict[str, Any]:
    config = get_config(key)
    for field in config["fields"]:
        if field["name"] == field_name:
            return field
    raise ValueError(f"Champ inconnu: {field_name}")


def _clean_values(config: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    allowed_names = {field["name"] for field in config["fields"]}

    for field in config["fields"]:
        name = field["name"]
        raw_value = values.get(name, field.get("default"))

        if name not in allowed_names:
            continue
        if field["type"] == "bool":
            cleaned[name] = 1 if raw_value in (1, True, "1", "true", "True", "on") else 0
        elif field["type"] in ("int", "fk"):
            cleaned[name] = int(raw_value) if raw_value not in ("", None) else None
        else:
            cleaned[name] = str(raw_value).strip() if raw_value is not None else ""

    return cleaned


def _validate_payload(config: dict[str, Any], payload: dict[str, Any]) -> None:
    for field in config["fields"]:
        value = payload.get(field["name"])
        if field.get("required") and value in ("", None):
            raise ValueError(f"Champ obligatoire: {field['label']}")
        if field["type"] == "int" and value is not None and value < 0:
            raise ValueError(f"Valeur invalide: {field['label']}")


def _friendly_integrity_error(exc: sqlite3.IntegrityError) -> str:
    message = str(exc)
    if "UNIQUE constraint failed" in message:
        return "Enregistrement impossible: une valeur unique existe deja."
    if "FOREIGN KEY constraint failed" in message:
        return "Enregistrement impossible: une relation obligatoire est invalide."
    if "CHECK constraint failed" in message:
        return "Enregistrement impossible: une valeur ne respecte pas la regle autorisee."
    return "Enregistrement impossible: contrainte de base de donnees non respectee."
