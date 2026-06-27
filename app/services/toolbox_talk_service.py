from __future__ import annotations

import calendar
import json
import random
from datetime import date, datetime
from typing import Any

from app.db.connection import db_session
from app.services.audit_service import record_system_audit

DEFAULT_TOOLBOX_FACILITATOR = "ABOU DIARRA"

# Guards the one-time bilingual normalization so it never runs in a read path.
_bilingual_normalization_done = False

DEFAULT_TOOLBOX_THEMES = [
    "Mandatory PPE selection and use / Port obligatoire des EPI adaptes a la tache",
    "Fatigue management before starting work / Gestion de la fatigue avant prise de poste",
    "Mobile equipment traffic and pedestrian segregation / Circulation des engins et separation pietons vehicules",
    "Job risk assessment: Stop, Think, Act / Analyse des risques avant travaux: Stop, Think, Act",
    "Working at height: harness, anchor points and inspection / Travail en hauteur: harnais, points d'ancrage et controle",
    "Slip, trip and fall prevention / Prevention des chutes de plain-pied et rangement des zones",
    "Lockout and isolation of hazardous energy / Consignation et isolation des energies dangereuses",
    "Manual handling and ergonomics / Manutention manuelle et prevention des TMS",
    "Near-miss and unsafe condition reporting / Signalement des presqu'accidents et conditions dangereuses",
    "Chemical management and SDS review / Gestion des produits chimiques et lecture des FDS",
    "Hydration, heat stress and sun protection / Hydratation, chaleur et prevention du stress thermique",
    "Fire response and correct extinguisher use / Utilisation correcte des extincteurs et alerte incendie",
    "Pre-operational inspection of tools and equipment / Controle pre-operationnel des outils et equipements",
    "Radio communication and field instructions / Communication radio et respect des instructions terrain",
    "Environmental protection: waste, hydrocarbons and dust / Protection de l'environnement: dechets, hydrocarbures et poussiere",
    "Fitness for work: alcohol and drug prohibition / Aptitude au travail: interdiction alcool et drogues",
    "Permit to work before critical activities / Permis de travail avant activite critique",
    "Housekeeping on drilling platforms / Ordre et proprete sur les plateformes de forage",
    "Mechanical work projection hazards / Prevention des projections lors des travaux mecaniques",
    "Hydraulic hoses, pressure lines and fittings / Controle des flexibles sous pression et raccords hydrauliques",
    "Blind spots around mobile equipment / Gestion des angles morts autour des equipements mobiles",
    "Site speed limits and defensive driving / Respect des limitations de vitesse sur site",
    "Emergency procedure and muster points / Procedure d'urgence et points de rassemblement",
    "Hot work fire prevention / Prevention des incendies lors des travaux a chaud",
    "Ladders and temporary access safety / Utilisation des echelles et acces temporaires",
    "Guardrails, grating and openings inspection / Verification des garde-corps, caillebotis et ouvertures",
    "Noise control and hearing protection / Prevention du bruit et port des protections auditives",
    "Dust control and respiratory protection / Gestion des poussieres et protection respiratoire",
    "Night work visibility, lighting and communication / Travaux de nuit: visibilite, eclairage et communication",
    "Excavation permits and buried services / Controle des permis d'excavation et reseaux enterres",
    "Lifting operations safety / Securite pendant les operations de levage",
    "Slings, chains and lifting accessories inspection / Inspection des sangles, chaines et accessoires de levage",
    "Barricading and signage of hazardous areas / Signalisation et balisage des zones dangereuses",
    "First aid: rapid alert and victim protection / Premiers secours: alerte rapide et protection de la victime",
    "Drilling procedures and restricted areas / Respect des procedures de forage et zones interdites",
    "Hand and finger pinch-point prevention / Prevention des coincements mains et doigts",
    "Visitor and contractor control on site / Gestion des visiteurs et sous-traitants sur site",
    "Defensive driving on mine roads / Conduite defensive sur piste miniere",
    "QHSE document control before work starts / Controle des documents QHSE avant demarrage travaux",
    "Incident and near-miss lessons learned / Retour d'experience apres incident ou presqu'accident",
]

TOOLBOX_SINGLE_LANGUAGE_TRANSLATIONS = {
    "port des epi": "Mandatory PPE selection and use / Port des EPI",
    "port obligatoire des epi": "Mandatory PPE selection and use / Port obligatoire des EPI",
    "controle des epi": "PPE inspection and control / Controle des EPI",
    "circulation sur site": "Site traffic management / Circulation sur site",
    "fatigue management": "Fatigue management before starting work / Gestion de la fatigue",
    "gestion de la fatigue": "Fatigue management before starting work / Gestion de la fatigue",
}


def current_toolbox_month() -> str:
    return date.today().strftime("%Y-%m")


def list_toolbox_topics(month: str | None = None) -> dict[str, Any]:
    selected_month = _parse_month(month or current_toolbox_month())
    year, month_number = map(int, selected_month.split("-"))
    days_in_month = calendar.monthrange(year, month_number)[1]
    start = f"{selected_month}-01"
    end = f"{selected_month}-{days_in_month:02d}"
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT
                ts.id_theme,
                ts.date_theme,
                ts.theme,
                ts.facilitateur,
                ts.site_id,
                s.nom AS site
            FROM themes_securite ts
            LEFT JOIN sites s ON s.id_site = ts.site_id
            WHERE ts.date_theme BETWEEN ? AND ?
            ORDER BY ts.date_theme
            """,
            (start, end),
        ).fetchall()
    by_date = {str(row["date_theme"]): dict(row) for row in rows}
    topic_rows = []
    for day in range(1, days_in_month + 1):
        day_date = f"{selected_month}-{day:02d}"
        existing = by_date.get(day_date)
        topic_rows.append(
            {
                "id_theme": existing.get("id_theme") if existing else None,
                "date_theme": day_date,
                "day": day,
                "weekday": _weekday_label(day_date),
                "theme": existing.get("theme") if existing else "",
                "facilitateur": existing.get("facilitateur") if existing else "",
                "site_id": existing.get("site_id") if existing else None,
                "site": existing.get("site") if existing else "",
                "status": "done" if existing and str(existing.get("theme") or "").strip() else "missing",
            }
        )
    completed = sum(1 for row in topic_rows if row["status"] == "done")
    return {
        "month": selected_month,
        "label": f"{calendar.month_name[month_number]} {year}",
        "rows": topic_rows,
        "summary": {
            "days": days_in_month,
            "completed": completed,
            "missing": days_in_month - completed,
            "completion": round(completed * 100 / days_in_month) if days_in_month else 0,
        },
    }


def get_toolbox_dashboard_snapshot(month: str | None = None) -> dict[str, Any]:
    data = list_toolbox_topics(month)
    selected_month = str(data["month"])
    days = _month_days(selected_month)
    with db_session() as connection:
        confirmations = connection.execute(
            """
            SELECT mtc.*, s.nom AS site
            FROM mobile_toolbox_confirmations mtc
            LEFT JOIN sites s ON s.id_site = mtc.site_id
            WHERE mtc.date_theme BETWEEN ? AND ?
            ORDER BY mtc.date_theme DESC, mtc.synced_at DESC
            """,
            (days[0], days[-1]),
        ).fetchall()
    confirmation_rows = [dict(row) for row in confirmations]
    confirmation_by_date = {str(row["date_theme"]): row for row in confirmation_rows}
    completed_rows = [row for row in data["rows"] if row["status"] == "done"]
    realized_rows = [row for row in completed_rows if row["date_theme"] in confirmation_by_date]
    attendees = sum(int(row.get("attendees_count") or 0) for row in confirmation_rows)
    facilitator_counts: dict[str, int] = {}
    site_counts: dict[str, int] = {}
    for row in completed_rows:
        facilitator = str(row.get("facilitateur") or "Non affecte")
        facilitator_counts[facilitator] = facilitator_counts.get(facilitator, 0) + 1
        site = str(row.get("site") or "Non affecte")
        site_counts[site] = site_counts.get(site, 0) + 1
    return {
        **data,
        "confirmations": confirmation_rows,
        "history": [
            {
                **row,
                "attendees_count": int((confirmation_by_date.get(str(row["date_theme"])) or {}).get("attendees_count") or 0),
                "comments": str((confirmation_by_date.get(str(row["date_theme"])) or {}).get("comments") or ""),
                "realized": str(row["date_theme"]) in confirmation_by_date,
            }
            for row in reversed(completed_rows)
        ],
        "facilitators": dict(sorted(facilitator_counts.items(), key=lambda item: item[1], reverse=True)),
        "sites": dict(sorted(site_counts.items(), key=lambda item: item[1], reverse=True)),
        "analytics": {
            "planned": len(completed_rows),
            "realized": len(realized_rows),
            "missing": int(data["summary"]["missing"]),
            "participants": attendees,
            "average_participants": round(attendees / max(len(realized_rows), 1), 1),
            "realization_rate": round(len(realized_rows) * 100 / max(len(completed_rows), 1)),
            "planning_rate": int(data["summary"]["completion"]),
            "active_facilitators": len(facilitator_counts),
        },
    }


def save_toolbox_topic(values: dict[str, Any]) -> int:
    payload = _clean_payload(values)
    with db_session() as connection:
        existing = connection.execute(
            "SELECT id_theme, theme, facilitateur FROM themes_securite WHERE date_theme = ?",
            (payload["date_theme"],),
        ).fetchone()
        _ensure_theme_not_used_in_month(connection, payload["date_theme"], payload["theme"])
        cursor = connection.execute(
            """
            INSERT INTO themes_securite(date_theme, theme, facilitateur, site_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date_theme) DO UPDATE SET
                theme = excluded.theme,
                facilitateur = excluded.facilitateur,
                site_id = excluded.site_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                payload["date_theme"],
                payload["theme"],
                payload["facilitateur"],
                payload["site_id"],
            ),
        )
        row = connection.execute(
            "SELECT id_theme FROM themes_securite WHERE date_theme = ?",
            (payload["date_theme"],),
        ).fetchone()
        topic_id = int(row["id_theme"] if row else cursor.lastrowid)
        action = "UPDATE" if existing else "CREATE"
        old_val = json.dumps({"theme": existing["theme"], "facilitateur": existing["facilitateur"]}) if existing else None
        new_val = json.dumps({"theme": payload["theme"], "facilitateur": payload["facilitateur"]})
        _log_toolbox_audit(connection, action, payload["date_theme"], payload["theme"], payload["facilitateur"], old_val, new_val)
    record_system_audit("save_toolbox_topic", "toolbox_topic", str(topic_id), f"date={payload['date_theme']}")
    return topic_id


def assign_topic_to_dates(values: dict[str, Any]) -> int:
    dates = [_parse_date(str(item)) for item in values.get("dates", []) if str(item or "").strip()]
    if not dates:
        raise ValueError("Selectionne au moins une date.")
    theme = _normalize_bilingual_theme(values.get("theme"))
    if not theme:
        raise ValueError("Theme / topic obligatoire.")
    months = {target_date[:7] for target_date in dates}
    for month in months:
        if sum(1 for target_date in set(dates) if target_date.startswith(month)) > 1:
            raise ValueError("Un theme ne peut pas etre affecte plusieurs fois dans le meme mois.")
    facilitator = _normalize_facilitator(values.get("facilitateur"))
    site_id = values.get("site_id")
    normalized_site_id = int(site_id) if site_id not in ("", None) else None
    with db_session() as connection:
        for target_date in sorted(set(dates)):
            _ensure_theme_not_used_in_month(connection, target_date, theme)
        for target_date in sorted(set(dates)):
            existing = connection.execute(
                "SELECT theme, facilitateur FROM themes_securite WHERE date_theme = ?",
                (target_date,),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO themes_securite(date_theme, theme, facilitateur, site_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(date_theme) DO UPDATE SET
                    theme = excluded.theme,
                    facilitateur = excluded.facilitateur,
                    site_id = excluded.site_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (target_date, theme, facilitator, normalized_site_id),
            )
            action = "UPDATE" if existing else "CREATE"
            old_val = json.dumps({"theme": existing["theme"], "facilitateur": existing["facilitateur"]}) if existing else None
            new_val = json.dumps({"theme": theme, "facilitateur": facilitator})
            _log_toolbox_audit(connection, action, target_date, theme, facilitator, old_val, new_val)
    return len(set(dates))


def list_theme_catalog(include_inactive: bool = False) -> list[dict[str, Any]]:
    where = "" if include_inactive else "WHERE actif = 1"
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT id_topic, theme, obligatoire, actif, created_at, updated_at
            FROM toolbox_theme_catalog
            {where}
            ORDER BY obligatoire DESC, theme
            """
        ).fetchall()
    return [dict(row) for row in rows]


def save_theme_catalog(values: dict[str, Any]) -> int:
    theme = _normalize_bilingual_theme(values.get("theme"))
    if not theme:
        raise ValueError("Theme obligatoire.")
    topic_id = int(values.get("id_topic") or 0)
    obligatoire = 1 if bool(values.get("obligatoire")) else 0
    actif = 1 if values.get("actif", True) else 0
    audit_action = "save_toolbox_theme"
    with db_session() as connection:
        if topic_id:
            cursor = connection.execute(
                """
                UPDATE toolbox_theme_catalog
                SET theme = ?, obligatoire = ?, actif = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id_topic = ?
                """,
                (theme, obligatoire, actif, topic_id),
            )
            if not cursor.rowcount:
                raise ValueError("Theme introuvable.")
            saved_id = topic_id
            audit_action = "update_toolbox_theme"
        else:
            cursor = connection.execute(
                """
                INSERT INTO toolbox_theme_catalog(theme, obligatoire, actif)
                VALUES (?, ?, ?)
                ON CONFLICT(theme) DO UPDATE SET
                    obligatoire = excluded.obligatoire,
                    actif = excluded.actif,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (theme, obligatoire, actif),
            )
            row = connection.execute(
                "SELECT id_topic FROM toolbox_theme_catalog WHERE theme = ?",
                (theme,),
            ).fetchone()
            saved_id = int(row["id_topic"] if row else cursor.lastrowid)
    record_system_audit(audit_action, "toolbox_theme_catalog", str(saved_id), theme)
    return saved_id


def delete_theme_catalog(topic_id: int) -> None:
    with db_session() as connection:
        cursor = connection.execute(
            "DELETE FROM toolbox_theme_catalog WHERE id_topic = ?",
            (int(topic_id),),
        )
        if not cursor.rowcount:
            raise ValueError("Theme introuvable dans la banque.")
    record_system_audit("delete_toolbox_theme", "toolbox_theme_catalog", str(topic_id), "Theme supprime")


def generate_toolbox_theme_catalog(count: int = 31) -> int:
    selected_count = max(1, min(int(count or 31), len(DEFAULT_TOOLBOX_THEMES)))
    existing = {_theme_key(row["theme"]) for row in list_theme_catalog(include_inactive=True)}
    created = 0
    for index, theme in enumerate(DEFAULT_TOOLBOX_THEMES[:selected_count]):
        if _theme_key(theme) in existing:
            continue
        save_theme_catalog(
            {
                "theme": theme,
                "obligatoire": index < 4,
                "actif": True,
            }
        )
        created += 1
    return created


def assign_monthly_topics(month: str | None = None, facilitateur: str | None = None, overwrite: bool = False) -> int:
    selected_month = _parse_month(month or current_toolbox_month())
    days = _month_days(selected_month)
    catalog = list_theme_catalog()
    if not catalog:
        raise ValueError("Cree au moins un theme avant l'affectation mensuelle.")
    selected_facilitator = str(facilitateur or "").strip() or None
    assigned = 0
    with db_session() as connection:
        existing_rows = connection.execute(
            """
            SELECT date_theme, theme
            FROM themes_securite
            WHERE date_theme BETWEEN ? AND ?
            """,
            (days[0], days[-1]),
        ).fetchall()
        existing_with_theme = {
            str(row["date_theme"])
            for row in existing_rows
            if str(row["theme"] or "").strip()
        }
        existing_theme_counts: dict[str, int] = {}
        if not overwrite:
            for row in existing_rows:
                theme = _normalize_bilingual_theme(row["theme"])
                if theme:
                    key = _theme_key(theme)
                    existing_theme_counts[key] = existing_theme_counts.get(key, 0) + 1
        target_days = [day for day in days if overwrite or day not in existing_with_theme]

        # Séparer les thèmes obligatoires des optionnels pour garantir leur présence
        mandatory_pool: list[str] = []
        optional_pool: list[str] = []
        for row in catalog:
            theme = _normalize_bilingual_theme(row["theme"])
            if not theme:
                continue
            already_used = existing_theme_counts.get(_theme_key(theme), 0)
            if already_used >= 1:
                continue
            if row.get("obligatoire"):
                mandatory_pool.append(theme)
            else:
                optional_pool.append(theme)

        random.shuffle(mandatory_pool)
        random.shuffle(optional_pool)
        # Les thèmes obligatoires d'abord, puis les optionnels
        theme_pool = mandatory_pool + optional_pool

        if len(theme_pool) < len(target_days):
            mandatory_count = len(mandatory_pool)
            optional_count = len(optional_pool)
            needed = len(target_days)
            available = len(theme_pool)
            raise ValueError(
                f"Themes insuffisants : {available} themes disponibles ({mandatory_count} obligatoires, "
                f"{optional_count} optionnels) pour {needed} jours a affecter. "
                f"Ajoute au moins {needed - available} theme(s) supplementaire(s) dans la banque."
            )

        for day in days:
            if day in existing_with_theme and not overwrite:
                continue
            theme = theme_pool.pop(0)
            connection.execute(
                """
                INSERT INTO themes_securite(date_theme, theme, facilitateur)
                VALUES (?, ?, COALESCE(?, ?))
                ON CONFLICT(date_theme) DO UPDATE SET
                    theme = excluded.theme,
                    facilitateur = CASE
                        WHEN ? IS NULL THEN COALESCE(themes_securite.facilitateur, excluded.facilitateur)
                        ELSE excluded.facilitateur
                    END,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (day, theme, selected_facilitator, DEFAULT_TOOLBOX_FACILITATOR, selected_facilitator),
            )
            _log_toolbox_audit(
                connection, "AUTO_ASSIGN", day, theme,
                selected_facilitator or DEFAULT_TOOLBOX_FACILITATOR,
                None,
                json.dumps({"theme": theme, "facilitateur": selected_facilitator or DEFAULT_TOOLBOX_FACILITATOR}),
            )
            assigned += 1
    record_system_audit("assign_monthly_toolbox_topics", "toolbox_month", selected_month, f"assigned={assigned}")
    return assigned


def apply_monthly_toolbox_facilitator(month: str | None = None, facilitateur: str | None = None) -> int:
    selected_month = _parse_month(month or current_toolbox_month())
    days = _month_days(selected_month)
    facilitator = _normalize_facilitator(facilitateur)
    with db_session() as connection:
        for day in days:
            connection.execute(
                """
                INSERT INTO themes_securite(date_theme, theme, facilitateur)
                VALUES (?, '', ?)
                ON CONFLICT(date_theme) DO UPDATE SET
                    facilitateur = excluded.facilitateur,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (day, facilitator),
            )
    return len(days)


def get_toolbox_topic_for_date(date_theme: str | None = None, auto_assign: bool = True) -> dict[str, Any] | None:
    target_date = _parse_date(date_theme or date.today().isoformat())
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT id_theme, date_theme, theme, facilitateur, site_id
            FROM themes_securite
            WHERE date_theme = ?
            """,
            (target_date,),
        ).fetchone()
    if row:
        return dict(row)
    if not auto_assign:
        return None
    try:
        assign_monthly_topics(target_date[:7])
    except ValueError:
        return None
    with db_session() as connection:
        assigned = connection.execute(
            """
            SELECT id_theme, date_theme, theme, facilitateur, site_id
            FROM themes_securite
            WHERE date_theme = ?
            """,
            (target_date,),
        ).fetchone()
    return dict(assigned) if assigned else None


def delete_toolbox_topic(date_theme: str) -> None:
    target_date = _parse_date(date_theme)
    with db_session() as connection:
        existing = connection.execute(
            "SELECT theme, facilitateur FROM themes_securite WHERE date_theme = ?",
            (target_date,),
        ).fetchone()
        connection.execute("DELETE FROM themes_securite WHERE date_theme = ?", (target_date,))
        if existing:
            _log_toolbox_audit(
                connection, "DELETE", target_date,
                existing["theme"], existing["facilitateur"],
                json.dumps({"theme": existing["theme"], "facilitateur": existing["facilitateur"]}),
                None,
            )


def save_desktop_confirmation(values: dict[str, Any]) -> int:
    target_date = _parse_date(str(values.get("date_theme") or ""))
    attendees = max(0, int(values.get("attendees_count") or 0))
    comments = str(values.get("comments") or "").strip() or None
    facilitator = str(values.get("facilitateur") or "").strip() or None
    site_id = values.get("site_id")
    normalized_site_id = int(site_id) if site_id not in ("", None) else None
    with db_session() as connection:
        topic_row = connection.execute(
            "SELECT theme, facilitateur, site_id FROM themes_securite WHERE date_theme = ?",
            (target_date,),
        ).fetchone()
        theme = str((topic_row["theme"] if topic_row else "") or "").strip()
        resolved_facilitator = facilitator or (str(topic_row["facilitateur"] or "") if topic_row else None) or DEFAULT_TOOLBOX_FACILITATOR
        resolved_site_id = normalized_site_id or (int(topic_row["site_id"]) if topic_row and topic_row["site_id"] else None)
        connection.execute(
            """
            INSERT INTO mobile_toolbox_confirmations
                (device_id, date_theme, theme, facilitator, site_id, attendees_count, comments, synced_at)
            VALUES ('DESKTOP', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(date_theme) DO UPDATE SET
                attendees_count = excluded.attendees_count,
                comments        = excluded.comments,
                facilitator     = excluded.facilitator,
                site_id         = excluded.site_id,
                theme           = excluded.theme,
                synced_at       = CURRENT_TIMESTAMP
            """,
            (target_date, theme, resolved_facilitator, resolved_site_id, attendees, comments),
        )
        row = connection.execute(
            "SELECT id_confirmation FROM mobile_toolbox_confirmations WHERE date_theme = ?",
            (target_date,),
        ).fetchone()
        confirmation_id = int(row["id_confirmation"]) if row else 0
    record_system_audit("save_desktop_confirmation", "mobile_toolbox_confirmations", str(confirmation_id), f"date={target_date};attendees={attendees}")
    return confirmation_id


def delete_desktop_confirmation(date_theme: str) -> None:
    target_date = _parse_date(date_theme)
    with db_session() as connection:
        connection.execute(
            "DELETE FROM mobile_toolbox_confirmations WHERE date_theme = ? AND device_id = 'DESKTOP'",
            (target_date,),
        )
    record_system_audit("delete_desktop_confirmation", "mobile_toolbox_confirmations", target_date, "Confirmation supprimee")


def clear_monthly_toolbox_topics(month: str | None = None) -> int:
    selected_month = _parse_month(month or current_toolbox_month())
    days = _month_days(selected_month)
    with db_session() as connection:
        cursor = connection.execute(
            """
            DELETE FROM themes_securite
            WHERE date_theme BETWEEN ? AND ?
            """,
            (days[0], days[-1]),
        )
        count = int(cursor.rowcount or 0)
        if count:
            _log_toolbox_audit(
                connection, "CLEAR_MONTH", None, None, None,
                json.dumps({"month": selected_month, "deleted": count}),
                None,
            )
        return count


def get_toolbox_options() -> dict[str, list[dict[str, Any]]]:
    with db_session() as connection:
        sites = connection.execute(
            """
            SELECT id_site AS value, nom AS label
            FROM sites
            WHERE actif = 1
            ORDER BY nom
            """
        ).fetchall()
    return {
        "sites": [dict(row) for row in sites],
        "themes": list_theme_catalog(),
        "facilitators": list_toolbox_facilitators(),
    }


def list_toolbox_facilitators() -> list[dict[str, str]]:
    names = {DEFAULT_TOOLBOX_FACILITATOR}
    with db_session() as connection:
        employee_rows = connection.execute(
            """
            SELECT nom_complet
            FROM employes
            WHERE statut = 'actif'
              AND COALESCE(nom_complet, '') <> ''
            ORDER BY nom_complet
            """
        ).fetchall()
        topic_rows = connection.execute(
            """
            SELECT DISTINCT facilitateur
            FROM themes_securite
            WHERE COALESCE(facilitateur, '') <> ''
            ORDER BY facilitateur
            """
        ).fetchall()
    for row in employee_rows:
        names.add(str(row["nom_complet"]).strip())
    for row in topic_rows:
        names.add(str(row["facilitateur"]).strip())
    ordered = [DEFAULT_TOOLBOX_FACILITATOR]
    ordered.extend(sorted(name for name in names if name and name != DEFAULT_TOOLBOX_FACILITATOR))
    return [{"value": name, "label": name} for name in ordered]


def get_toolbox_stats(months_back: int = 6) -> dict[str, Any]:
    """Statistiques avancées Toolbox Talk : complétion mensuelle, par site, par facilitateur."""
    today = date.today()
    months = []
    for offset in range(months_back - 1, -1, -1):
        m = today.month - offset
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        months.append(f"{y}-{m:02d}")

    with db_session() as connection:
        monthly_stats = []
        for month in months:
            year, month_number = map(int, month.split("-"))
            days_in_month = calendar.monthrange(year, month_number)[1]
            start = f"{month}-01"
            end = f"{month}-{days_in_month:02d}"
            completed = connection.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM themes_securite
                WHERE date_theme BETWEEN ? AND ?
                  AND COALESCE(theme, '') <> ''
                """,
                (start, end),
            ).fetchone()["cnt"]
            completion = round(completed * 100 / days_in_month) if days_in_month else 0
            label = f"{calendar.month_abbr[month_number]} {year}"
            monthly_stats.append({
                "month": month,
                "label": label,
                "days": days_in_month,
                "completed": int(completed),
                "missing": days_in_month - int(completed),
                "completion": completion,
            })

        # Stats par facilitateur (6 derniers mois)
        start_all = f"{months[0]}-01"
        year_last, month_last_num = map(int, months[-1].split("-"))
        days_last = calendar.monthrange(year_last, month_last_num)[1]
        end_all = f"{months[-1]}-{days_last:02d}"

        facilitator_rows = connection.execute(
            """
            SELECT
                COALESCE(facilitateur, 'Non renseigne') AS facilitateur,
                COUNT(*) AS total
            FROM themes_securite
            WHERE date_theme BETWEEN ? AND ?
              AND COALESCE(theme, '') <> ''
            GROUP BY COALESCE(facilitateur, 'Non renseigne')
            ORDER BY total DESC
            LIMIT 10
            """,
            (start_all, end_all),
        ).fetchall()
        by_facilitator = [{"facilitateur": r["facilitateur"], "total": int(r["total"])} for r in facilitator_rows]

        # Stats par site (6 derniers mois)
        site_rows = connection.execute(
            """
            SELECT
                COALESCE(s.nom, 'Non renseigne') AS site,
                COUNT(*) AS total
            FROM themes_securite ts
            LEFT JOIN sites s ON s.id_site = ts.site_id
            WHERE ts.date_theme BETWEEN ? AND ?
              AND COALESCE(ts.theme, '') <> ''
            GROUP BY COALESCE(s.nom, 'Non renseigne')
            ORDER BY total DESC
            """,
            (start_all, end_all),
        ).fetchall()
        by_site = [{"site": r["site"], "total": int(r["total"])} for r in site_rows]

        # Total global
        total_done = sum(m["completed"] for m in monthly_stats)
        total_days = sum(m["days"] for m in monthly_stats)
        global_completion = round(total_done * 100 / total_days) if total_days else 0

    return {
        "monthly": monthly_stats,
        "by_facilitator": by_facilitator,
        "by_site": by_site,
        "global": {
            "total_done": total_done,
            "total_days": total_days,
            "completion": global_completion,
        },
    }


def list_toolbox_audit(month: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    where = ""
    params: tuple[Any, ...] = ()
    if month:
        selected_month = _parse_month(month)
        days = _month_days(selected_month)
        where = "WHERE (date_theme BETWEEN ? AND ? OR date_theme IS NULL)"
        params = (days[0], days[-1])
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT id_audit, action, date_theme, theme, facilitateur,
                   ancienne_valeur, nouvelle_valeur, changed_by, changed_at, commentaire
            FROM toolbox_audit
            {where}
            ORDER BY changed_at DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def _log_toolbox_audit(
    connection: Any,
    action: str,
    date_theme: str | None,
    theme: str | None,
    facilitateur: str | None,
    old_val: str | None,
    new_val: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO toolbox_audit(action, date_theme, theme, facilitateur, ancienne_valeur, nouvelle_valeur)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (action, date_theme, theme, facilitateur, old_val, new_val),
    )


def _clean_payload(values: dict[str, Any]) -> dict[str, Any]:
    target_date = _parse_date(str(values.get("date_theme") or ""))
    theme = _normalize_bilingual_theme(values.get("theme"))
    facilitator = _normalize_facilitator(values.get("facilitateur"))
    site_id = values.get("site_id")
    if not theme:
        raise ValueError("Theme / topic obligatoire.")
    return {
        "date_theme": target_date,
        "theme": theme,
        "facilitateur": facilitator,
        "site_id": int(site_id) if site_id not in ("", None) else None,
    }


def run_bilingual_normalization_once() -> None:
    """Run the bilingual topic migration exactly once per process lifetime.

    Call this at application startup (e.g. after initialize_database). Never
    call it inside a read path — it performs UPDATEs on every row.
    """
    global _bilingual_normalization_done
    if _bilingual_normalization_done:
        return
    with db_session() as connection:
        _normalize_existing_bilingual_topics(connection)
    _bilingual_normalization_done = True


def _normalize_existing_bilingual_topics(connection: Any) -> None:
    # Hardcoded queries — no dynamic identifiers, zero injection surface
    _TABLE_QUERIES = (
        (
            "SELECT id_theme AS pk, theme FROM themes_securite",
            "UPDATE themes_securite SET theme = ?, updated_at = CURRENT_TIMESTAMP WHERE id_theme = ?",
        ),
        (
            "SELECT id_topic AS pk, theme FROM toolbox_theme_catalog",
            "UPDATE toolbox_theme_catalog SET theme = ?, updated_at = CURRENT_TIMESTAMP WHERE id_topic = ?",
        ),
    )
    for select_sql, update_sql in _TABLE_QUERIES:
        rows = connection.execute(select_sql).fetchall()
        for row in rows:
            current = str(row["theme"] or "").strip()
            normalized = _normalize_bilingual_theme(current)
            if current and normalized != current:
                connection.execute(update_sql, (normalized, row["pk"]))


def _normalize_bilingual_theme(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if _has_bilingual_separator(text):
        english, french = _split_theme_parts(text)
        return f"{english} / {french}" if english and french else text
    translated = TOOLBOX_SINGLE_LANGUAGE_TRANSLATIONS.get(_plain_key(text))
    if translated:
        return translated
    # Pas de traduction automatique disponible : on retourne le texte tel quel
    # pour éviter la duplication "texte / texte" qui n'est pas bilingue
    return text


def _ensure_theme_not_used_in_month(connection: Any, target_date: str, theme: str) -> None:
    month = str(target_date)[:7]
    start = f"{month}-01"
    end = _month_days(month)[-1]
    theme_key = _theme_key(theme)
    rows = connection.execute(
        """
        SELECT date_theme, theme
        FROM themes_securite
        WHERE date_theme BETWEEN ? AND ?
          AND date_theme <> ?
          AND COALESCE(theme, '') <> ''
        """,
        (start, end, target_date),
    ).fetchall()
    for row in rows:
        if _theme_key(row["theme"]) == theme_key:
            raise ValueError(
                f"Ce theme est deja utilise le {row['date_theme']} dans ce mois. Choisis un autre theme."
            )


def _has_bilingual_separator(value: str) -> bool:
    return any(separator in str(value or "") for separator in (" / ", " | "))


def _split_theme_parts(value: str) -> tuple[str, str]:
    separator = " / " if " / " in value else " | "
    left, right = [part.strip() for part in value.split(separator, 1)]
    left_language = _detect_theme_language(left)
    right_language = _detect_theme_language(right)
    if left_language == "fr" and right_language != "fr":
        return right, left
    if right_language == "en" and left_language != "en":
        return right, left
    return left, right


def _detect_theme_language(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "unknown"
    french_words = {
        "analyse", "avant", "circulation", "controle", "de", "des", "du", "engins",
        "epi", "et", "fatigue", "gestion", "hauteur", "la", "le", "les", "obligatoire",
        "pietons", "port", "prevention", "risques", "securite", "site", "travail", "travaux",
    }
    english_words = {
        "and", "before", "control", "equipment", "fatigue", "height", "inspection",
        "job", "management", "mandatory", "mobile", "ppe", "prevention", "risk",
        "safety", "site", "traffic", "use", "work", "working",
    }
    normalized = "".join(char if char.isalnum() else " " for char in text)
    tokens = normalized.split()
    french_score = sum(1 for token in tokens if token in french_words)
    english_score = sum(1 for token in tokens if token in english_words)
    if any(char in text for char in "àâçéèêëîïôùûü"):
        french_score += 2
    if french_score > english_score:
        return "fr"
    if english_score > french_score:
        return "en"
    return "unknown"


def _theme_key(value: Any) -> str:
    return _plain_key(_normalize_bilingual_theme(value))


def _plain_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    return " ".join("".join(char if char.isalnum() else " " for char in text).split())


def _normalize_facilitator(value: Any) -> str:
    return str(value or "").strip() or DEFAULT_TOOLBOX_FACILITATOR


def _parse_month(value: str) -> str:
    try:
        datetime.strptime(str(value), "%Y-%m")
    except ValueError as exc:
        raise ValueError("Format mois invalide. Utilise AAAA-MM.") from exc
    return str(value)


def _parse_date(value: str) -> str:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("Format date invalide. Utilise AAAA-MM-JJ.") from exc


def _weekday_label(value: str) -> str:
    labels = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    return labels[datetime.strptime(value, "%Y-%m-%d").weekday()]


def _month_days(month: str) -> list[str]:
    selected_month = _parse_month(month)
    year, month_number = map(int, selected_month.split("-"))
    days_in_month = calendar.monthrange(year, month_number)[1]
    return [f"{selected_month}-{day:02d}" for day in range(1, days_in_month + 1)]


# ── Nouvelles fonctions analytiques ─────────────────────────────────────────

def get_today_toolbox_session() -> dict[str, Any]:
    today = date.today().isoformat()
    with db_session() as connection:
        topic = connection.execute(
            """
            SELECT ts.id_theme, ts.date_theme, ts.theme, ts.facilitateur, ts.site_id, s.nom AS site
            FROM themes_securite ts
            LEFT JOIN sites s ON s.id_site = ts.site_id
            WHERE ts.date_theme = ?
            """,
            (today,),
        ).fetchone()
        conf = connection.execute(
            "SELECT attendees_count, comments, device_id FROM mobile_toolbox_confirmations WHERE date_theme = ?",
            (today,),
        ).fetchone()
    topic_dict = dict(topic) if topic else None
    return {
        "date": today,
        "weekday": _weekday_label(today),
        "has_topic": bool(topic_dict and str(topic_dict.get("theme") or "").strip()),
        "topic": topic_dict,
        "confirmed": bool(conf),
        "attendees": int((conf or {}).get("attendees_count") or 0) if conf else 0,
        "device": str((conf or {}).get("device_id") or "") if conf else "",
    }


def detect_facilitator_conflicts(month: str | None = None) -> list[dict[str, Any]]:
    selected_month = _parse_month(month or current_toolbox_month())
    days = _month_days(selected_month)
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT ts.date_theme, ts.facilitateur,
                   GROUP_CONCAT(COALESCE(s.nom, 'Site inconnu'), ' | ') AS sites,
                   COUNT(DISTINCT COALESCE(ts.site_id, -ts.id_theme)) AS site_count
            FROM themes_securite ts
            LEFT JOIN sites s ON s.id_site = ts.site_id
            WHERE ts.date_theme BETWEEN ? AND ?
              AND COALESCE(ts.facilitateur, '') <> ''
              AND ts.site_id IS NOT NULL
            GROUP BY ts.date_theme, ts.facilitateur
            HAVING COUNT(DISTINCT ts.site_id) > 1
            ORDER BY ts.date_theme
            """,
            (days[0], days[-1]),
        ).fetchall()
    return [dict(row) for row in rows]


def get_toolbox_trend_data(months: int = 6) -> list[dict[str, Any]]:
    today = date.today()
    result: list[dict[str, Any]] = []
    for i in range(months - 1, -1, -1):
        total_months = today.year * 12 + today.month - 1 - i
        y = total_months // 12
        m = total_months % 12 + 1
        month_str = f"{y}-{m:02d}"
        try:
            data = list_toolbox_topics(month_str)
        except ValueError:
            continue
        days = _month_days(month_str)
        with db_session() as connection:
            confs = connection.execute(
                "SELECT COUNT(*) AS count, SUM(attendees_count) AS total FROM mobile_toolbox_confirmations WHERE date_theme BETWEEN ? AND ?",
                (days[0], days[-1]),
            ).fetchone()
        completed = int(data["summary"]["completed"])
        total_days = int(data["summary"]["days"])
        realized = int(confs["count"] or 0) if confs else 0
        participants = int(confs["total"] or 0) if confs else 0
        result.append({
            "month": month_str,
            "label": f"{calendar.month_abbr[m]}",
            "planned": completed,
            "realized": realized,
            "participants": participants,
            "completion_rate": int(data["summary"]["completion"]),
            "realization_rate": round(realized * 100 / max(completed, 1)),
            "days": total_days,
        })
    return result
