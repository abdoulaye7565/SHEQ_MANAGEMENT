from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from app.db.connection import db_session, safe_sql_identifier
from app.services.employee_service import (
    BADGE_STATUSES,
    EMPLOYEE_STATUSES,
    EMPLOYEE_TYPES,
    create_employee,
)


HEADER_ALIASES = {
    "matricule": {"matricule", "employee id", "id employe", "id employee", "code"},
    "nom": {"nom", "last name", "lastname", "surname"},
    "prenom": {"prenom", "first name", "firstname"},
    "nom_complet": {"nom complet", "full name", "employee", "employe", "name", "nom et prenom"},
    "numero_badge": {"badge", "numero badge", "numero_badge", "badge number", "no badge"},
    "fonction": {"fonction", "poste", "job", "position", "function"},
    "site": {"site", "location", "localisation"},
    "groupe": {"groupe", "group", "equipe", "team"},
    "shift": {"shift", "quart", "horaire"},
    "type_employe": {"type employe", "employee type", "type", "national expatriate"},
    "statut_employe": {"statut", "statut employe", "status", "employee status"},
    "statut_badge": {"statut badge", "badge status"},
    "date_remise": {"date remise", "date remise badge", "badge issue date", "issue date"},
    "date_expiration_badge": {"date expiration badge", "expiration badge", "badge expiry", "badge expiration"},
}


REQUIRED_IMPORT_FIELDS = {"fonction", "site", "shift"}


def import_employees_from_file(path: str | Path, dry_run: bool = False) -> dict[str, Any]:
    source = Path(path)
    rows = read_employee_import_rows(source)
    prepared, errors = prepare_employee_import(rows)
    if errors:
        return {"created": 0, "dry_run": dry_run, "rows": len(rows), "errors": errors}
    if dry_run:
        return {"created": 0, "dry_run": True, "rows": len(rows), "errors": [], "preview": prepared[:10]}

    created = 0
    created_ids: list[int] = []
    for payload in prepared:
        try:
            created_ids.append(create_employee(payload))
            created += 1
        except ValueError as exc:
            errors.append({"line": payload["_line"], "message": str(exc)})
    return {
        "created": created,
        "created_ids": created_ids,
        "dry_run": False,
        "rows": len(rows),
        "errors": errors,
    }


def read_employee_import_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_csv_rows(path)
    if suffix == ".xlsx":
        return _read_xlsx_rows(path)
    raise ValueError("Format non supporte. Utilise un fichier CSV ou XLSX.")


def prepare_employee_import(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    references = _load_references()
    prepared: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen_matricules: set[str] = set()
    seen_badges: set[str] = set()

    for index, row in enumerate(rows, start=2):
        normalized = _normalize_row(row)
        if not any(str(value or "").strip() for value in normalized.values()):
            continue
        line_errors = _validate_import_row(normalized, references)
        matricule = str(normalized.get("matricule") or "").strip()
        badge = str(normalized.get("numero_badge") or "").strip()
        if matricule:
            key = matricule.lower()
            if key in seen_matricules:
                line_errors.append("Matricule en doublon dans le fichier.")
            seen_matricules.add(key)
        if badge:
            key = badge.lower()
            if key in seen_badges:
                line_errors.append("Numero badge en doublon dans le fichier.")
            seen_badges.add(key)
        if matricule and _normalize_text(matricule) in references["matricules"]:
            line_errors.append("Matricule deja existant dans la base.")
        if badge and _normalize_text(badge) in references["badges"]:
            line_errors.append("Numero badge deja existant dans la base.")
        if line_errors:
            errors.extend({"line": index, "message": message} for message in line_errors)
            continue
        prepared.append(_payload_from_row(normalized, references, index))

    if not prepared and not errors:
        errors.append({"line": 1, "message": "Aucune ligne employe trouvee dans le fichier."})
    return prepared, errors


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;	")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    return [dict(row) for row in reader]


def _read_xlsx_rows(path: Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = _xlsx_shared_strings(archive)
        sheet_name = _first_sheet_path(archive)
        root = ElementTree.fromstring(archive.read(sheet_name))

    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    matrix: list[list[str]] = []
    for row in root.findall(".//main:sheetData/main:row", namespace):
        values: dict[int, str] = {}
        for cell in row.findall("main:c", namespace):
            ref = str(cell.attrib.get("r") or "")
            column = _xlsx_column_index(ref)
            values[column] = _xlsx_cell_value(cell, shared_strings, namespace)
        if values:
            max_column = max(values)
            matrix.append([values.get(col, "") for col in range(1, max_column + 1)])
    if not matrix:
        return []
    header_index = _xlsx_header_row_index(matrix)
    headers = [str(item or "") for item in matrix[header_index]]
    rows = []
    for row in matrix[header_index + 1 :]:
        if _xlsx_is_footer_row(row):
            break
        rows.append({headers[index]: value for index, value in enumerate(row) if index < len(headers)})
    return rows


def _xlsx_header_row_index(matrix: list[list[str]]) -> int:
    best_index = 0
    best_score = 0
    for index, row in enumerate(matrix[:20]):
        canonical = {_canonical_header(value) for value in row if str(value or "").strip()}
        score = len({value for value in canonical if value})
        if score > best_score:
            best_index = index
            best_score = score
        if REQUIRED_IMPORT_FIELDS.issubset({value for value in canonical if value}):
            return index
    return best_index


def _xlsx_is_footer_row(row: list[str]) -> bool:
    values = {_normalize_text(value) for value in row if str(value or "").strip()}
    return bool(
        values
        and (
            {"prepared by", "checked by", "approved by"} & values
            or "name date signature" in values
        )
    )


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    strings = []
    for item in root.findall("main:si", namespace):
        parts = [text.text or "" for text in item.findall(".//main:t", namespace)]
        strings.append("".join(parts))
    return strings


def _first_sheet_path(archive: zipfile.ZipFile) -> str:
    names = sorted(name for name in archive.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", name))
    if not names:
        raise ValueError("Aucune feuille trouvee dans le fichier XLSX.")
    return names[0]


def _xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str], namespace: dict[str, str]) -> str:
    cell_type = cell.attrib.get("t")
    value = cell.find("main:v", namespace)
    if value is None:
        inline = cell.find(".//main:t", namespace)
        return inline.text if inline is not None and inline.text else ""
    text = value.text or ""
    if cell_type == "s":
        try:
            return shared_strings[int(text)]
        except (ValueError, IndexError):
            return ""
    return text


def _xlsx_column_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + (ord(char.upper()) - 64)
    return index or 1


def _normalize_row(row: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for source_header, value in row.items():
        key = _canonical_header(source_header)
        if key:
            normalized[key] = str(value or "").strip()
    return normalized


def _canonical_header(header: Any) -> str | None:
    clean = _normalize_text(str(header or ""))
    for field, aliases in HEADER_ALIASES.items():
        if clean in {_normalize_text(alias) for alias in aliases}:
            return field
    return None


def _validate_import_row(row: dict[str, str], references: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    name = _employee_name(row)
    if not name:
        errors.append("Nom/prenom ou nom complet obligatoire.")
    for field in REQUIRED_IMPORT_FIELDS:
        if not row.get(field):
            errors.append(f"Champ obligatoire manquant: {field}.")
    if row.get("fonction") and _lookup_reference(references["fonctions"], row["fonction"]) is None:
        errors.append(f"Fonction introuvable: {row['fonction']}.")
    if row.get("site") and _lookup_reference(references["sites"], row["site"]) is None:
        errors.append(f"Site introuvable: {row['site']}.")
    if row.get("groupe") and _lookup_reference(references["groupes"], row["groupe"]) is None:
        errors.append(f"Groupe introuvable: {row['groupe']}.")
    if row.get("shift") and _lookup_reference(references["shifts"], row["shift"]) is None:
        errors.append(f"Shift introuvable: {row['shift']}.")
    employee_type = _normalize_employee_type(row.get("type_employe") or "national")
    if employee_type not in EMPLOYEE_TYPES:
        errors.append("Type employe invalide. Valeurs: national, expatriate.")
    employee_status = _normalize_status(row.get("statut_employe") or "actif")
    if employee_status not in EMPLOYEE_STATUSES:
        errors.append("Statut employe invalide.")
    badge_status = _normalize_status(row.get("statut_badge") or "valide")
    if badge_status not in BADGE_STATUSES:
        errors.append("Statut badge invalide.")
    return errors


def _payload_from_row(
    row: dict[str, str],
    references: dict[str, dict[str, Any]],
    line: int,
) -> dict[str, Any]:
    payload = {
        "matricule": row.get("matricule") or None,
        "nom": row.get("nom") or None,
        "prenom": row.get("prenom") or None,
        "nom_complet": _employee_name(row),
        "fonction_id": _lookup_reference(references["fonctions"], row["fonction"]),
        "site_id": _lookup_reference(references["sites"], row["site"]),
        "groupe_id": _lookup_reference(references["groupes"], row.get("groupe") or ""),
        "shift_id": _lookup_reference(references["shifts"], row["shift"]),
        "type_employe": _normalize_employee_type(row.get("type_employe") or "national"),
        "statut_employe": _normalize_status(row.get("statut_employe") or "actif"),
        "numero_badge": row.get("numero_badge") or None,
        "statut_badge": _normalize_status(row.get("statut_badge") or "valide"),
        "date_remise": row.get("date_remise") or None,
        "date_expiration_badge": row.get("date_expiration_badge") or None,
        "_line": line,
    }
    return payload


def _load_references() -> dict[str, dict[str, Any]]:
    with db_session() as connection:
        return {
            "fonctions": _reference_map(connection, "fonctions", "id_fonction", ["nom"]),
            "sites": _reference_map(connection, "sites", "id_site", ["nom"]),
            "groupes": _reference_map(connection, "groupes", "id_groupe", ["nom"]),
            "shifts": _reference_map(connection, "shifts", "id_shift", ["code", "libelle"]),
            "matricules": _existing_values(connection, "employes", "matricule"),
            "badges": _existing_values(connection, "badges", "numero_badge"),
        }


def _reference_map(connection: Any, table: str, pk: str, labels: list[str]) -> dict[str, int]:
    t = safe_sql_identifier(table)
    p = safe_sql_identifier(pk)
    cols = ", ".join(safe_sql_identifier(lbl) for lbl in labels)
    rows = connection.execute(f"SELECT {p}, {cols} FROM {t}").fetchall()
    mapping: dict[str, int] = {}
    for row in rows:
        for label in labels:
            value = row[label]
            if value:
                mapping[_normalize_text(str(value))] = int(row[pk])
    return mapping


def _lookup_reference(mapping: dict[str, Any], value: str) -> int | None:
    clean = _normalize_text(value)
    return int(mapping[clean]) if clean in mapping else None


def _existing_values(connection: Any, table: str, column: str) -> dict[str, bool]:
    t = safe_sql_identifier(table)
    c = safe_sql_identifier(column)
    rows = connection.execute(f"SELECT {c} FROM {t} WHERE {c} IS NOT NULL").fetchall()
    return {_normalize_text(str(row[column])): True for row in rows if row[column]}


def _employee_name(row: dict[str, str]) -> str:
    if row.get("nom") or row.get("prenom"):
        return " ".join(part for part in [row.get("nom"), row.get("prenom")] if part).strip()
    return str(row.get("nom_complet") or "").strip()


def _normalize_employee_type(value: str) -> str:
    clean = _normalize_text(value)
    if clean in {"expat", "expatrie", "expatriate"}:
        return "expatriate"
    return clean or "national"


def _normalize_status(value: str) -> str:
    clean = _normalize_text(value)
    return {
        "active": "actif",
        "valid": "valide",
        "validé": "valide",
        "validee": "valide",
        "non conforme": "non conforme",
    }.get(clean, clean)


def _normalize_text(value: str) -> str:
    text = str(value or "").strip().lower()
    replacements = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "à": "a",
        "â": "a",
        "î": "i",
        "ï": "i",
        "ô": "o",
        "ù": "u",
        "û": "u",
        "_": " ",
        "-": " ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return " ".join(text.split())
