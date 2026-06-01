from __future__ import annotations

import calendar
import random
from datetime import date, datetime
from typing import Any

from app.db.connection import db_session

DEFAULT_TOOLBOX_FACILITATOR = "ABOU DIARRA"

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


def save_toolbox_topic(values: dict[str, Any]) -> int:
    payload = _clean_payload(values)
    with db_session() as connection:
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
        return int(row["id_theme"] if row else cursor.lastrowid)


def assign_topic_to_dates(values: dict[str, Any]) -> int:
    dates = [_parse_date(str(item)) for item in values.get("dates", []) if str(item or "").strip()]
    if not dates:
        raise ValueError("Selectionne au moins une date.")
    theme = str(values.get("theme") or "").strip()
    if not theme:
        raise ValueError("Theme / topic obligatoire.")
    facilitator = _normalize_facilitator(values.get("facilitateur"))
    site_id = values.get("site_id")
    normalized_site_id = int(site_id) if site_id not in ("", None) else None
    with db_session() as connection:
        for target_date in sorted(set(dates)):
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
    theme = str(values.get("theme") or "").strip()
    if not theme:
        raise ValueError("Theme obligatoire.")
    topic_id = int(values.get("id_topic") or 0)
    obligatoire = 1 if bool(values.get("obligatoire")) else 0
    actif = 1 if values.get("actif", True) else 0
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
            return topic_id
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
        return int(row["id_topic"] if row else cursor.lastrowid)


def generate_toolbox_theme_catalog(count: int = 31) -> int:
    selected_count = max(1, min(int(count or 31), len(DEFAULT_TOOLBOX_THEMES)))
    existing = {str(row["theme"]).strip().lower() for row in list_theme_catalog(include_inactive=True)}
    created = 0
    for index, theme in enumerate(DEFAULT_TOOLBOX_THEMES[:selected_count]):
        if theme.lower() in existing:
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
                theme = str(row["theme"] or "").strip()
                if theme:
                    existing_theme_counts[theme] = existing_theme_counts.get(theme, 0) + 1
        target_days = [day for day in days if overwrite or day not in existing_with_theme]
        theme_pool: list[str] = []
        for row in catalog:
            theme = str(row["theme"] or "").strip()
            if not theme:
                continue
            limit = 2 if int(row.get("obligatoire") or 0) else 1
            remaining = limit - existing_theme_counts.get(theme, 0)
            theme_pool.extend([theme] * max(0, remaining))
        random.shuffle(theme_pool)
        if len(theme_pool) < len(target_days):
            raise ValueError(
                "Themes insuffisants pour remplir le mois avec cette regle: "
                "un theme normal une seule fois, un theme obligatoire deux fois maximum."
            )
        for day in days:
            if day in existing_with_theme and not overwrite:
                continue
            theme = theme_pool.pop()
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
            assigned += 1
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
    assign_monthly_topics(target_date[:7])
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
        connection.execute("DELETE FROM themes_securite WHERE date_theme = ?", (target_date,))


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
        return int(cursor.rowcount or 0)


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


def _clean_payload(values: dict[str, Any]) -> dict[str, Any]:
    target_date = _parse_date(str(values.get("date_theme") or ""))
    theme = str(values.get("theme") or "").strip()
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
