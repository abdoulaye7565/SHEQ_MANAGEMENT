from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Any

from app.db.connection import db_session
from app.services.audit_service import record_system_audit
from app.services.toolbox_talk_service import current_toolbox_month, save_theme_catalog


TOOLBOX_CATEGORIES = [
    "HSE General",
    "Driving",
    "Working at Height",
    "Confined Space",
    "Lifting",
    "RC Drilling",
    "Diamond Drilling",
    "PPE",
    "Housekeeping",
    "Environment",
    "Fire Fighting",
    "First Aid",
    "Fatigue",
    "LOTO",
    "Machine Guarding",
    "Journey Management",
]
TOOLBOX_RISK_LEVELS = ["faible", "moyen", "eleve", "critique"]
TOOLBOX_FREQUENCIES = [
    "quotidienne",
    "hebdomadaire",
    "mensuelle",
    "trimestrielle",
    "semestrielle",
    "annuelle",
]
TOOLBOX_THEME_STATUSES = ["actif", "en_attente", "inactif", "obsolete"]


def list_professional_toolbox_themes(filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    selected = filters or {}
    where: list[str] = []
    params: list[Any] = []
    search = str(selected.get("search") or "").strip()
    if search:
        pattern = f"%{search}%"
        where.append(
            """
            (catalog.code_theme LIKE ? OR catalog.theme LIKE ? OR catalog.topic_en LIKE ?
             OR catalog.theme_fr LIKE ? OR catalog.category LIKE ?)
            """
        )
        params.extend([pattern] * 5)
    for field in ("category", "risk_level", "frequency", "status"):
        value = str(selected.get(field) or "all")
        if value != "all":
            where.append(f"catalog.{field} = ?")
            params.append(value)
    site_id = selected.get("site_id")
    if site_id not in (None, "", "all"):
        where.append("catalog.site_id = ?")
        params.append(int(site_id))
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT catalog.*, sites.nom AS site, departments.nom AS department
            FROM toolbox_theme_catalog catalog
            LEFT JOIN sites ON sites.id_site = catalog.site_id
            LEFT JOIN departments ON departments.id_department = catalog.department_id
            {clause}
            ORDER BY
                CASE catalog.risk_level
                    WHEN 'critique' THEN 0 WHEN 'eleve' THEN 1 WHEN 'moyen' THEN 2 ELSE 3
                END,
                catalog.obligatoire DESC,
                catalog.code_theme
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def save_professional_toolbox_theme(values: dict[str, Any]) -> int:
    topic_en = _required_text(values.get("topic_en"), "Topic EN")
    theme_fr = _required_text(values.get("theme_fr"), "Theme FR")
    category = _choice(values.get("category"), TOOLBOX_CATEGORIES, "Categorie HSE")
    risk_level = _choice(values.get("risk_level"), TOOLBOX_RISK_LEVELS, "Niveau de risque")
    frequency = _choice(values.get("frequency"), TOOLBOX_FREQUENCIES, "Frequence")
    status = _choice(values.get("status"), TOOLBOX_THEME_STATUSES, "Statut")
    topic_id = save_theme_catalog(
        {
            "id_topic": values.get("id_topic"),
            "theme": f"{topic_en} / {theme_fr}",
            "obligatoire": bool(values.get("obligatoire")),
            "actif": status == "actif",
        }
    )
    with db_session() as connection:
        connection.execute(
            """
            UPDATE toolbox_theme_catalog
            SET code_theme = COALESCE(NULLIF(?, ''), printf('TBX-%03d', id_topic)),
                category = ?,
                risk_level = ?,
                topic_en = ?,
                theme_fr = ?,
                frequency = ?,
                site_id = ?,
                department_id = ?,
                status = ?,
                actif = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id_topic = ?
            """,
            (
                str(values.get("code_theme") or "").strip(),
                category,
                risk_level,
                topic_en,
                theme_fr,
                frequency,
                _optional_id(values.get("site_id")),
                _optional_id(values.get("department_id")),
                status,
                1 if status == "actif" else 0,
                topic_id,
            ),
        )
    record_system_audit("save_professional_toolbox_theme", "toolbox_theme_catalog", str(topic_id), f"{category};{risk_level}")
    return topic_id


def synchronize_toolbox_theme_usage() -> int:
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO toolbox_theme_usage (
                topic_id, theme_id, usage_date, site_id, department_id,
                facilitator, participants_count, observation, source
            )
            SELECT
                catalog.id_topic,
                planned.id_theme,
                planned.date_theme,
                planned.site_id,
                sites.department_id,
                planned.facilitateur,
                COALESCE(confirmation.attendees_count, 0),
                confirmation.comments,
                CASE WHEN confirmation.id_confirmation IS NULL THEN 'planning' ELSE 'mobile_confirmation' END
            FROM themes_securite planned
            JOIN toolbox_theme_catalog catalog ON TRIM(catalog.theme) = TRIM(planned.theme)
            LEFT JOIN sites ON sites.id_site = planned.site_id
            LEFT JOIN mobile_toolbox_confirmations confirmation
              ON confirmation.date_theme = planned.date_theme
             AND (confirmation.site_id = planned.site_id OR confirmation.site_id IS NULL OR planned.site_id IS NULL)
            WHERE COALESCE(TRIM(planned.theme), '') <> ''
              AND NOT EXISTS (
                  SELECT 1 FROM toolbox_theme_usage usage WHERE usage.theme_id = planned.id_theme
              )
            """
        )
        connection.execute(
            """
            UPDATE toolbox_theme_catalog
            SET usage_count = (SELECT COUNT(*) FROM toolbox_theme_usage usage WHERE usage.topic_id = toolbox_theme_catalog.id_topic),
                last_used_at = (SELECT MAX(usage_date) FROM toolbox_theme_usage usage WHERE usage.topic_id = toolbox_theme_catalog.id_topic)
            """
        )
    return int(cursor.rowcount or 0)


def list_toolbox_theme_usage(topic_id: int | None = None) -> list[dict[str, Any]]:
    synchronize_toolbox_theme_usage()
    where = "WHERE usage.topic_id = ?" if topic_id else ""
    params = (int(topic_id),) if topic_id else ()
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT usage.*, catalog.code_theme, catalog.topic_en, catalog.theme_fr,
                   sites.nom AS site, departments.nom AS department
            FROM toolbox_theme_usage usage
            LEFT JOIN toolbox_theme_catalog catalog ON catalog.id_topic = usage.topic_id
            LEFT JOIN sites ON sites.id_site = usage.site_id
            LEFT JOIN departments ON departments.id_department = usage.department_id
            {where}
            ORDER BY usage.usage_date DESC, usage.id_usage DESC
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def save_toolbox_effectiveness(values: dict[str, Any]) -> int:
    usage_id = int(values.get("usage_id") or 0)
    if usage_id <= 0:
        raise ValueError("Session Toolbox obligatoire.")
    participation = _score(values.get("participation_rate"), "Taux de participation")
    comprehension = _score(values.get("comprehension_score"), "Score de comprehension")
    facilitator = _score(values.get("facilitator_rating"), "Note facilitateur")
    quality = _score(values.get("session_quality"), "Qualite session")
    global_score = round(participation * 0.30 + comprehension * 0.45 + facilitator * 0.15 + quality * 0.10, 2)
    with db_session() as connection:
        connection.execute(
            """
            INSERT INTO toolbox_effectiveness_evaluations (
                usage_id, participation_rate, comprehension_score, facilitator_rating,
                session_quality, global_score, comments, evaluated_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(usage_id) DO UPDATE SET
                participation_rate = excluded.participation_rate,
                comprehension_score = excluded.comprehension_score,
                facilitator_rating = excluded.facilitator_rating,
                session_quality = excluded.session_quality,
                global_score = excluded.global_score,
                comments = excluded.comments,
                evaluated_by = excluded.evaluated_by,
                evaluated_at = CURRENT_TIMESTAMP
            """,
            (
                usage_id,
                participation,
                comprehension,
                facilitator,
                quality,
                global_score,
                str(values.get("comments") or "").strip() or None,
                str(values.get("evaluated_by") or "system").strip(),
            ),
        )
        evaluation = connection.execute(
            "SELECT id_evaluation FROM toolbox_effectiveness_evaluations WHERE usage_id = ?",
            (usage_id,),
        ).fetchone()
        connection.execute(
            """
            UPDATE toolbox_theme_catalog
            SET average_effectiveness = COALESCE((
                SELECT ROUND(AVG(evaluation.global_score), 2)
                FROM toolbox_effectiveness_evaluations evaluation
                JOIN toolbox_theme_usage usage ON usage.id_usage = evaluation.usage_id
                WHERE usage.topic_id = toolbox_theme_catalog.id_topic
            ), 0)
            """
        )
    evaluation_id = int(evaluation["id_evaluation"])
    record_system_audit("save_toolbox_effectiveness", "toolbox_effectiveness", str(evaluation_id), f"score={global_score}")
    return evaluation_id


def list_toolbox_effectiveness() -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT evaluation.*, usage.usage_date, usage.facilitator, usage.participants_count,
                   catalog.code_theme, catalog.topic_en, catalog.theme_fr
            FROM toolbox_effectiveness_evaluations evaluation
            JOIN toolbox_theme_usage usage ON usage.id_usage = evaluation.usage_id
            LEFT JOIN toolbox_theme_catalog catalog ON catalog.id_topic = usage.topic_id
            ORDER BY evaluation.evaluated_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def save_toolbox_campaign(values: dict[str, Any]) -> int:
    name = _required_text(values.get("name"), "Nom campagne")
    start_date = _required_text(values.get("start_date"), "Date debut")
    end_date = _required_text(values.get("end_date"), "Date fin")
    if end_date < start_date:
        raise ValueError("La date de fin doit etre posterieure a la date de debut.")
    campaign_id = int(values.get("id_campaign") or 0)
    with db_session() as connection:
        if campaign_id:
            connection.execute(
                """
                UPDATE toolbox_campaigns
                SET code_campaign = ?, name = ?, description = ?, category = ?, start_date = ?,
                    end_date = ?, site_id = ?, department_id = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id_campaign = ?
                """,
                _campaign_payload(values, name, start_date, end_date) + (campaign_id,),
            )
        else:
            cursor = connection.execute(
                """
                INSERT INTO toolbox_campaigns (
                    code_campaign, name, description, category, start_date, end_date,
                    site_id, department_id, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _campaign_payload(values, name, start_date, end_date),
            )
            campaign_id = int(cursor.lastrowid)
        for topic_id in {int(item) for item in values.get("topic_ids", []) if int(item) > 0}:
            connection.execute(
                "INSERT OR IGNORE INTO toolbox_campaign_themes(campaign_id, topic_id) VALUES (?, ?)",
                (campaign_id, topic_id),
            )
    record_system_audit("save_toolbox_campaign", "toolbox_campaign", str(campaign_id), name)
    return campaign_id


def list_toolbox_campaigns(active_only: bool = False) -> list[dict[str, Any]]:
    where = "WHERE campaign.status = 'active' AND campaign.start_date <= ? AND campaign.end_date >= ?" if active_only else ""
    params = (date.today().isoformat(), date.today().isoformat()) if active_only else ()
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT campaign.*, sites.nom AS site, departments.nom AS department,
                   COUNT(link.topic_id) AS themes_count
            FROM toolbox_campaigns campaign
            LEFT JOIN toolbox_campaign_themes link ON link.campaign_id = campaign.id_campaign
            LEFT JOIN sites ON sites.id_site = campaign.site_id
            LEFT JOIN departments ON departments.id_department = campaign.department_id
            {where}
            GROUP BY campaign.id_campaign
            ORDER BY campaign.start_date DESC
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def get_toolbox_theme_bank_statistics(month: str | None = None) -> dict[str, Any]:
    synchronize_toolbox_theme_usage()
    selected_month = str(month or current_toolbox_month())
    with db_session() as connection:
        summary = connection.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN status = 'actif' THEN 1 ELSE 0 END) AS active,
                   SUM(CASE WHEN risk_level = 'critique' THEN 1 ELSE 0 END) AS critical,
                   SUM(CASE WHEN status = 'en_attente' THEN 1 ELSE 0 END) AS pending,
                   ROUND(AVG(average_effectiveness), 1) AS effectiveness
            FROM toolbox_theme_catalog
            """
        ).fetchone()
        used = connection.execute(
            "SELECT COUNT(DISTINCT topic_id) AS count FROM toolbox_theme_usage WHERE substr(usage_date, 1, 7) = ?",
            (selected_month,),
        ).fetchone()
        category_rows = connection.execute(
            "SELECT category, COUNT(*) AS count FROM toolbox_theme_catalog GROUP BY category ORDER BY count DESC"
        ).fetchall()
        risk_rows = connection.execute(
            "SELECT risk_level, COUNT(*) AS count FROM toolbox_theme_catalog GROUP BY risk_level ORDER BY count DESC"
        ).fetchall()
    total = int(summary["total"] or 0)
    used_count = int(used["count"] or 0)
    return {
        "total": total,
        "active": int(summary["active"] or 0),
        "critical": int(summary["critical"] or 0),
        "used_month": used_count,
        "pending": int(summary["pending"] or 0),
        "coverage_rate": round(used_count * 100 / max(total, 1)),
        "average_effectiveness": float(summary["effectiveness"] or 0),
        "by_category": {str(row["category"] or "Non classe"): int(row["count"]) for row in category_rows},
        "by_risk": {str(row["risk_level"] or "moyen"): int(row["count"]) for row in risk_rows},
    }


def get_toolbox_theme_bank_alerts(month: str | None = None) -> list[dict[str, Any]]:
    selected_month = str(month or current_toolbox_month())
    alerts: list[dict[str, Any]] = []
    with db_session() as connection:
        critical = connection.execute(
            """
            SELECT code_theme, theme FROM toolbox_theme_catalog
            WHERE risk_level = 'critique' AND status = 'actif'
              AND (last_used_at IS NULL OR last_used_at < DATE('now', '-90 days'))
            """
        ).fetchall()
        mandatory = connection.execute(
            """
            SELECT code_theme, theme FROM toolbox_theme_catalog catalog
            WHERE obligatoire = 1 AND status = 'actif'
              AND NOT EXISTS (
                  SELECT 1 FROM toolbox_theme_usage usage
                  WHERE usage.topic_id = catalog.id_topic AND substr(usage.usage_date, 1, 7) = ?
              )
            """,
            (selected_month,),
        ).fetchall()
        obsolete = connection.execute(
            "SELECT code_theme, theme FROM toolbox_theme_catalog WHERE status = 'obsolete'"
        ).fetchall()
        repeated = connection.execute(
            """
            SELECT catalog.code_theme, catalog.theme, COUNT(*) AS count
            FROM toolbox_theme_usage usage
            JOIN toolbox_theme_catalog catalog ON catalog.id_topic = usage.topic_id
            WHERE substr(usage.usage_date, 1, 7) = ? AND catalog.obligatoire = 0
            GROUP BY usage.topic_id HAVING COUNT(*) > 1
            """,
            (selected_month,),
        ).fetchall()
    alerts.extend(_alert_rows(critical, "critique_non_utilise", "Critique", "Theme critique non utilise depuis plus de 90 jours"))
    alerts.extend(_alert_rows(mandatory, "obligatoire_non_planifie", "Attention", "Theme obligatoire non planifie ce mois"))
    alerts.extend(_alert_rows(obsolete, "obsolete", "Attention", "Theme obsolete a revoir"))
    alerts.extend(_alert_rows(repeated, "repetition", "Attention", "Theme trop souvent repete ce mois"))
    return alerts


def get_toolbox_theme_bank_options() -> dict[str, Any]:
    with db_session() as connection:
        sites = [dict(row) for row in connection.execute("SELECT id_site AS value, nom AS label FROM sites WHERE actif = 1 ORDER BY nom")]
        departments = [
            dict(row)
            for row in connection.execute("SELECT id_department AS value, nom AS label FROM departments WHERE actif = 1 ORDER BY nom")
        ]
    return {
        "categories": TOOLBOX_CATEGORIES,
        "risk_levels": TOOLBOX_RISK_LEVELS,
        "frequencies": TOOLBOX_FREQUENCIES,
        "statuses": TOOLBOX_THEME_STATUSES,
        "sites": sites,
        "departments": departments,
    }


def generate_intelligent_toolbox_planning(
    month: str | None = None,
    facilitator: str | None = None,
    site_id: int | str | None = None,
    department_id: int | str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    selected_month = _parse_month(month or current_toolbox_month())
    selected_site = _optional_id(site_id)
    selected_department = _optional_id(department_id)
    year, month_number = map(int, selected_month.split("-"))
    days = [f"{selected_month}-{day:02d}" for day in range(1, calendar.monthrange(year, month_number)[1] + 1)]
    selected_facilitator = str(facilitator or "").strip() or None
    with db_session() as connection:
        existing_rows = connection.execute(
            """
            SELECT date_theme, theme FROM themes_securite
            WHERE date_theme BETWEEN ? AND ?
            """,
            (days[0], days[-1]),
        ).fetchall()
        existing_dates = {
            str(row["date_theme"])
            for row in existing_rows
            if str(row["theme"] or "").strip()
        }
        existing_themes = {
            str(row["theme"] or "").strip().lower()
            for row in existing_rows
            if str(row["theme"] or "").strip()
        }
        candidates = [
            dict(row)
            for row in connection.execute(
                """
                SELECT catalog.*,
                       CASE WHEN EXISTS (
                           SELECT 1
                           FROM toolbox_campaign_themes link
                           JOIN toolbox_campaigns campaign ON campaign.id_campaign = link.campaign_id
                           WHERE link.topic_id = catalog.id_topic
                             AND campaign.status = 'active'
                             AND campaign.start_date <= ?
                             AND campaign.end_date >= ?
                             AND (campaign.site_id IS NULL OR campaign.site_id = ? OR ? IS NULL)
                             AND (campaign.department_id IS NULL OR campaign.department_id = ? OR ? IS NULL)
                       ) THEN 1 ELSE 0 END AS active_campaign,
                       (
                           SELECT COUNT(*) FROM toolbox_theme_usage usage
                           WHERE usage.topic_id = catalog.id_topic
                             AND substr(usage.usage_date, 1, 7) = ?
                       ) AS used_this_month
                FROM toolbox_theme_catalog catalog
                WHERE catalog.status = 'actif'
                  AND catalog.actif = 1
                  AND (catalog.site_id IS NULL OR catalog.site_id = ? OR ? IS NULL)
                  AND (catalog.department_id IS NULL OR catalog.department_id = ? OR ? IS NULL)
                """,
                (
                    days[-1],
                    days[0],
                    selected_site,
                    selected_site,
                    selected_department,
                    selected_department,
                    selected_month,
                    selected_site,
                    selected_site,
                    selected_department,
                    selected_department,
                ),
            ).fetchall()
        ]
        if not candidates:
            raise ValueError("Aucun theme professionnel actif ne correspond au site et au departement selectionnes.")
        category_counts: dict[str, int] = {}
        for row in existing_rows:
            catalog = connection.execute(
                "SELECT category FROM toolbox_theme_catalog WHERE TRIM(LOWER(theme)) = TRIM(LOWER(?)) LIMIT 1",
                (row["theme"],),
            ).fetchone()
            category = str(catalog["category"] if catalog else "HSE General")
            category_counts[category] = category_counts.get(category, 0) + 1
        scored = [
            {
                **candidate,
                "priority_score": _theme_priority_score(candidate, days[0], category_counts),
                "frequency_due": _frequency_is_due(candidate, days[0]),
            }
            for candidate in candidates
        ]
        scored.sort(key=lambda row: (-float(row["priority_score"]), str(row["code_theme"] or row["theme"])))
        target_days = [day for day in days if overwrite or day not in existing_dates]
        assignments: list[dict[str, Any]] = []
        used_keys = set() if overwrite else set(existing_themes)
        for target_day in target_days:
            available = [
                row
                for row in scored
                if str(row["theme"]).strip().lower() not in used_keys and bool(row["frequency_due"])
            ]
            if not available:
                available = [
                    row
                    for row in scored
                    if bool(row["obligatoire"]) and bool(row["frequency_due"])
                ]
            if not available:
                break
            selected = available[0]
            theme = str(selected["theme"])
            connection.execute(
                """
                INSERT INTO themes_securite(date_theme, theme, facilitateur, site_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(date_theme) DO UPDATE SET
                    theme = excluded.theme,
                    facilitateur = COALESCE(excluded.facilitateur, themes_securite.facilitateur),
                    site_id = COALESCE(excluded.site_id, themes_securite.site_id),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (target_day, theme, selected_facilitator, selected_site),
            )
            used_keys.add(theme.strip().lower())
            category = str(selected.get("category") or "HSE General")
            category_counts[category] = category_counts.get(category, 0) + 1
            assignments.append(
                {
                    "date_theme": target_day,
                    "topic_id": int(selected["id_topic"]),
                    "theme": theme,
                    "priority_score": round(float(selected["priority_score"]), 2),
                    "repeated": sum(1 for item in assignments if item["topic_id"] == int(selected["id_topic"])) > 0,
                }
            )
    synchronize_toolbox_theme_usage()
    record_system_audit(
        "generate_intelligent_toolbox_planning",
        "toolbox_month",
        selected_month,
        f"assigned={len(assignments)};site={selected_site};department={selected_department}",
    )
    return {
        "month": selected_month,
        "assigned": len(assignments),
        "remaining": len(target_days) - len(assignments),
        "assignments": assignments,
    }


def preview_intelligent_toolbox_planning(
    month: str | None = None,
    facilitator: str | None = None,
    site_id: int | str | None = None,
    skip_weekends: bool = True,
) -> dict[str, Any]:
    """Compute the intelligent plan and return it WITHOUT saving to the database."""
    selected_month = _parse_month(month or current_toolbox_month())
    selected_site = _optional_id(site_id)
    year, month_number = map(int, selected_month.split("-"))
    days_raw = [f"{selected_month}-{day:02d}" for day in range(1, calendar.monthrange(year, month_number)[1] + 1)]
    if skip_weekends:
        days_raw = [d for d in days_raw if datetime.strptime(d, "%Y-%m-%d").weekday() < 5]
    selected_facilitator = str(facilitator or "").strip() or None

    with db_session() as connection:
        existing_rows = connection.execute(
            "SELECT date_theme, theme FROM themes_securite WHERE date_theme BETWEEN ? AND ?",
            (days_raw[0], days_raw[-1]),
        ).fetchall()
        existing_dates = {str(row["date_theme"]) for row in existing_rows if str(row["theme"] or "").strip()}
        existing_themes = {str(row["theme"] or "").strip().lower() for row in existing_rows if str(row["theme"] or "").strip()}

        candidates = [
            dict(row)
            for row in connection.execute(
                """
                SELECT catalog.*,
                       CASE WHEN EXISTS (
                           SELECT 1 FROM toolbox_campaign_themes link
                           JOIN toolbox_campaigns campaign ON campaign.id_campaign = link.campaign_id
                           WHERE link.topic_id = catalog.id_topic
                             AND campaign.status = 'active'
                             AND campaign.start_date <= ? AND campaign.end_date >= ?
                             AND (campaign.site_id IS NULL OR campaign.site_id = ? OR ? IS NULL)
                       ) THEN 1 ELSE 0 END AS active_campaign,
                       (SELECT COUNT(*) FROM toolbox_theme_usage u WHERE u.topic_id = catalog.id_topic AND substr(u.usage_date,1,7)=?) AS used_this_month
                FROM toolbox_theme_catalog catalog
                WHERE catalog.status = 'actif' AND catalog.actif = 1
                  AND (catalog.site_id IS NULL OR catalog.site_id = ? OR ? IS NULL)
                """,
                (days_raw[-1], days_raw[0], selected_site, selected_site, selected_month, selected_site, selected_site),
            ).fetchall()
        ]

        category_counts: dict[str, int] = {}
        for row in existing_rows:
            cat_row = connection.execute(
                "SELECT category FROM toolbox_theme_catalog WHERE TRIM(LOWER(theme)) = TRIM(LOWER(?)) LIMIT 1",
                (row["theme"],),
            ).fetchone()
            cat = str(cat_row["category"] if cat_row else "HSE General")
            category_counts[cat] = category_counts.get(cat, 0) + 1

    if not candidates:
        return {"month": selected_month, "preview": [], "total_days": len(days_raw), "already_planned": len(existing_dates)}

    scored = sorted(
        [
            {**c, "priority_score": _theme_priority_score(c, days_raw[0], category_counts), "frequency_due": _frequency_is_due(c, days_raw[0])}
            for c in candidates
        ],
        key=lambda r: (-float(r["priority_score"]), str(r["code_theme"] or r["theme"])),
    )

    target_days = [d for d in days_raw if d not in existing_dates]
    preview: list[dict[str, Any]] = []
    used_keys = set(existing_themes)
    local_category_counts = dict(category_counts)

    for target_day in target_days:
        available = [r for r in scored if str(r["theme"]).strip().lower() not in used_keys and bool(r["frequency_due"])]
        if not available:
            available = [r for r in scored if bool(r.get("obligatoire")) and bool(r["frequency_due"])]
        if not available:
            break
        sel = available[0]
        theme = str(sel["theme"])
        used_keys.add(theme.strip().lower())
        cat = str(sel.get("category") or "HSE General")
        local_category_counts[cat] = local_category_counts.get(cat, 0) + 1
        preview.append({
            "date_theme": target_day,
            "weekday": datetime.strptime(target_day, "%Y-%m-%d").strftime("%a"),
            "topic_en": str(sel.get("topic_en") or theme.split(" / ")[0]),
            "theme_fr": str(sel.get("theme_fr") or (theme.split(" / ")[1] if " / " in theme else theme)),
            "code_theme": str(sel.get("code_theme") or ""),
            "category": cat,
            "risk_level": str(sel.get("risk_level") or "moyen"),
            "obligatoire": bool(sel.get("obligatoire")),
            "active_campaign": bool(sel.get("active_campaign")),
            "priority_score": round(float(sel["priority_score"]), 1),
            "facilitateur": selected_facilitator or "",
        })

    return {
        "month": selected_month,
        "preview": preview,
        "total_days": len(days_raw),
        "already_planned": len(existing_dates),
        "new_assignments": len(preview),
    }


def _campaign_payload(values: dict[str, Any], name: str, start_date: str, end_date: str) -> tuple[Any, ...]:
    return (
        str(values.get("code_campaign") or "").strip() or None,
        name,
        str(values.get("description") or "").strip() or None,
        str(values.get("category") or "").strip() or None,
        start_date,
        end_date,
        _optional_id(values.get("site_id")),
        _optional_id(values.get("department_id")),
        str(values.get("status") or "planifiee").strip(),
    )


def _alert_rows(rows: list[Any], key: str, level: str, message: str) -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "level": level,
            "code_theme": str(row["code_theme"] or "-"),
            "theme": str(row["theme"] or "-"),
            "message": message,
        }
        for row in rows
    ]


def _required_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} obligatoire.")
    return text


def _choice(value: Any, choices: list[str], label: str) -> str:
    selected = _required_text(value, label)
    if selected not in choices:
        raise ValueError(f"{label} invalide.")
    return selected


def _optional_id(value: Any) -> int | None:
    return int(value) if value not in (None, "", "all") else None


def _score(value: Any, label: str) -> float:
    try:
        score = float(value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} invalide.") from exc
    if score < 0 or score > 100:
        raise ValueError(f"{label}: utilise une valeur entre 0 et 100.")
    return score


def _theme_priority_score(theme: dict[str, Any], planning_date: str, category_counts: dict[str, int]) -> float:
    risk_score = {"faible": 10, "moyen": 25, "eleve": 45, "critique": 70}.get(str(theme.get("risk_level")), 25)
    mandatory_score = 55 if theme.get("obligatoire") else 0
    campaign_score = 45 if theme.get("active_campaign") else 0
    due_score = 40 if _frequency_is_due(theme, planning_date) else -100
    last_used_score = _days_since_last_use(theme.get("last_used_at"), planning_date) / 10
    coverage_score = max(0, 25 - category_counts.get(str(theme.get("category") or "HSE General"), 0) * 5)
    effectiveness = float(theme.get("average_effectiveness") or 0)
    effectiveness_score = 12 if effectiveness == 0 else max(0, (80 - effectiveness) / 4)
    return risk_score + mandatory_score + campaign_score + due_score + last_used_score + coverage_score + effectiveness_score


def _frequency_is_due(theme: dict[str, Any], planning_date: str) -> bool:
    last_used = str(theme.get("last_used_at") or "")
    if not last_used:
        return True
    interval_days = {
        "quotidienne": 1,
        "hebdomadaire": 7,
        "mensuelle": 28,
        "trimestrielle": 90,
        "semestrielle": 180,
        "annuelle": 365,
    }.get(str(theme.get("frequency") or "mensuelle"), 28)
    return _days_since_last_use(last_used, planning_date) >= interval_days


def _days_since_last_use(last_used: Any, planning_date: str) -> int:
    if not last_used:
        return 365
    try:
        return max(0, (datetime.strptime(planning_date, "%Y-%m-%d") - datetime.strptime(str(last_used), "%Y-%m-%d")).days)
    except ValueError:
        return 365


def _parse_month(value: str) -> str:
    try:
        return datetime.strptime(str(value), "%Y-%m").strftime("%Y-%m")
    except ValueError as exc:
        raise ValueError("Format mois invalide. Utilise AAAA-MM.") from exc
