from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.components.tables import professional_data_table
from app.services import (
    DEFAULT_TOOLBOX_FACILITATOR,
    apply_monthly_toolbox_facilitator,
    assign_topic_to_dates,
    assign_monthly_topics,
    clear_monthly_toolbox_topics,
    current_toolbox_month,
    delete_toolbox_topic,
    delete_theme_catalog,
    detect_facilitator_conflicts,
    export_session_attendance_xlsx,
    export_toolbox_talk_xlsx,
    generate_intelligent_toolbox_planning,
    generate_toolbox_theme_catalog,
    get_today_toolbox_session,
    get_toolbox_theme_bank_alerts,
    get_toolbox_theme_bank_options,
    get_toolbox_theme_bank_statistics,
    get_toolbox_dashboard_snapshot,
    get_toolbox_options,
    get_toolbox_trend_data,
    list_professional_toolbox_themes,
    list_toolbox_campaigns,
    list_toolbox_effectiveness,
    list_toolbox_theme_usage,
    list_theme_catalog,
    list_toolbox_topics,
    preview_intelligent_toolbox_planning,
    save_professional_toolbox_theme,
    save_toolbox_campaign,
    save_toolbox_effectiveness,
    save_theme_catalog,
    save_toolbox_topic,
)
from app.services.toolbox_talk_service import (
    save_desktop_confirmation,
    delete_desktop_confirmation,
)
from app.services.ai_service import AIConfigurationError, suggest_toolbox_theme
from app.ui.components.feedback import show_feedback
from app.ui.components.module_header import module_header
from app.ui.components.pagination import PAGE_SIZE, pagination_row
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING

# ── Palette ───────────────────────────────────────────────────────────────────
_W   = "#FFFFFF"
_BSF = "#EFF6FF"
_BBD = "#BFDBFE"
_BHD = "#DBEAFE"
_GSF = "#F0FDF4"
_GBD = "#BBF7D0"
_RSF = "#FEF2F2"
_RBD = "#FECACA"
_ASF = "#FFFBEB"
_ABD = "#FDE68A"
_PSF = "#F5F3FF"
_PBD = "#DDD6FE"
_SLT = "#F8FAFC"
_SBD = "#E2E8F0"
_PRP = "#8B5CF6"
_TEAL    = "#0D9488"
_TEAL_SF = "#F0FDFA"
_TEAL_BD = "#99F6E4"
_TAB_OFF_BG = "#F1F5F9"
_TAB_OFF_FG = "#64748B"

# dark-cockpit palette (Banque des themes)
_DK_CARD   = "#0D2040"
_DK_CARD2  = "#0A1929"
_DK_HEAD   = "#112240"
_DK_BORDER = "#1E3A5F"
_DK_TEXT   = "#E2E8F0"
_DK_MUTED  = "#9DB0C5"
_DK_TRACK  = "#1A3050"


# ═══════════════════════════════════════════════════════════════════════════════
def toolbox_talk_page(page: ft.Page | None = None) -> ft.Control:  # noqa: C901
    state: dict[str, Any] = {
        "data": None, "snapshot": {}, "themes": [],
        "editing_topic_id": None, "editing_campaign_id": None,
        "selected_dates": set(), "tab": "dashboard",
        "plan_mode": "intelligent", "skip_weekends": True,
        "preview_result": None, "bank_form_visible": False,
        "page_campaigns": 0,
    }

    # ── zones dynamiques ─────────────────────────────────────────────────────
    summary_row      = ft.ResponsiveRow(spacing=12, run_spacing=12)
    today_banner     = ft.Column(spacing=0, visible=False)
    dashboard_area   = ft.Column(spacing=14)
    planning_area    = ft.Column(spacing=14)
    realization_area = ft.Column(spacing=10)
    bank_area        = ft.Column(spacing=14)
    history_area     = ft.Column(spacing=14)
    campaigns_area   = ft.Column(spacing=14)
    preview_area     = ft.Column(spacing=10, visible=False)

    status_txt   = ft.Text("", size=12, color=MUTED)
    options      = get_toolbox_options()
    bank_options = get_toolbox_theme_bank_options()

    # ── helpers ───────────────────────────────────────────────────────────────
    def _dd(label: str, width: int, opts: list, val: str = "") -> ft.Dropdown:
        return ft.Dropdown(label=label, value=val, width=width,
                           border_radius=8, fill_color="#0A1929", color="#E2E8F0",
                           border_color="#1E3A5F", focused_border_color="#2563EB",
                           label_style=ft.TextStyle(color="#9DB0C5"),
                           text_style=ft.TextStyle(color="#E2E8F0"), options=opts)

    def _tf(label: str, width: int = 0, hint: str = "", multiline: bool = False,
            min_lines: int = 1, max_lines: int = 4) -> ft.TextField:
        kw: dict[str, Any] = dict(label=label, hint_text=hint, border_radius=8,
                                  fill_color="#0A1929", color="#E2E8F0",
                                  border_color="#1E3A5F", focused_border_color="#2563EB",
                                  label_style=ft.TextStyle(color="#9DB0C5"),
                                  text_style=ft.TextStyle(color="#E2E8F0"),
                                  multiline=multiline, min_lines=min_lines, max_lines=max_lines)
        if width:
            kw["width"] = width
        return ft.TextField(**kw)

    def _facilitator_opts(current: str | None = None) -> list[ft.dropdown.Option]:
        names = [str(r["label"]) for r in options.get("facilitators", [])]
        sel = str(current or "").strip()
        if sel and sel not in names:
            names.append(sel)
        if DEFAULT_TOOLBOX_FACILITATOR not in names:
            names.insert(0, DEFAULT_TOOLBOX_FACILITATOR)
        return [ft.dropdown.Option(n, n) for n in names]

    # champs réalisation / planning
    month_field       = _tf("Mois", 150, "AAAA-MM"); month_field.value = current_toolbox_month()
    status_filter     = _dd("Etat", 170, [
        ft.dropdown.Option("all","Tous"), ft.dropdown.Option("done","Renseigne"),
        ft.dropdown.Option("missing","A completer")], "all")
    date_field        = _tf("Date(s)", 200, "AAAA-MM-JJ")
    topic_field       = _dd("Topic EN / Theme FR", 500, [])
    facilitator_field = _dd("Facilitateur", 260, _facilitator_opts(), DEFAULT_TOOLBOX_FACILITATOR)
    site_field        = _dd("Site", 200,
        [ft.dropdown.Option("","-")] + [ft.dropdown.Option(str(r["value"]),str(r["label"])) for r in options["sites"]])

    # champs confirmation
    attendees_field = _tf("Participants", 130, "0"); attendees_field.value = "0"
    comments_field  = _tf("Observations", multiline=True, min_lines=2, max_lines=3)

    # champs banque
    topic_en_field     = _tf("Topic EN", hint="Safety topic in English")
    theme_fr_field     = _tf("Theme FR", hint="Theme de securite en francais")
    category_field     = _dd("Categorie HSE", 200,
        [ft.dropdown.Option(v,v) for v in bank_options["categories"]], "HSE General")
    risk_level_field   = _dd("Niveau de risque", 170,
        [ft.dropdown.Option(v, v.title()) for v in bank_options["risk_levels"]], "moyen")
    frequency_field    = _dd("Frequence", 170,
        [ft.dropdown.Option(v, v.title()) for v in bank_options["frequencies"]], "mensuelle")
    theme_status_field = _dd("Statut", 160,
        [ft.dropdown.Option(v, v.replace("_"," ").title()) for v in bank_options["statuses"]], "actif")
    pro_site_field     = _dd("Site", 190,
        [ft.dropdown.Option("","Tous")] + [ft.dropdown.Option(str(r["value"]),str(r["label"])) for r in bank_options["sites"]])
    pro_obligatoire    = ft.Checkbox(label="Obligatoire")
    generated_count_field = _tf("Nb themes a generer", 150); generated_count_field.value = "31"

    # filtres banque (barre de recherche / filtrage)
    bank_search_tf   = _tf("Rechercher code, theme, categorie...", hint="")
    bank_cat_filter  = _dd("Categorie", 185,
        [ft.dropdown.Option("","Toutes")] + [ft.dropdown.Option(v,v) for v in bank_options["categories"]])
    bank_risk_filter = _dd("Niveau de risque", 165,
        [ft.dropdown.Option("","Tous")] + [ft.dropdown.Option(v, v.title()) for v in bank_options["risk_levels"]])
    bank_freq_filter = _dd("Frequence", 155,
        [ft.dropdown.Option("","Toutes")] + [ft.dropdown.Option(v, v.title()) for v in bank_options["frequencies"]])
    bank_stat_filter = _dd("Statut", 150,
        [ft.dropdown.Option("","Tous")] + [ft.dropdown.Option(v, v.replace("_"," ").title()) for v in bank_options["statuses"]])
    bank_site_filter = _dd("Site", 175,
        [ft.dropdown.Option("","Tous sites")] + [ft.dropdown.Option(str(r["value"]),str(r["label"])) for r in bank_options["sites"]])
    # styling dark pour la barre de filtre uniquement
    for _fd in (bank_cat_filter, bank_risk_filter, bank_freq_filter, bank_stat_filter, bank_site_filter):
        _fd.fill_color  = _DK_CARD2
        _fd.border_color = _DK_BORDER
        _fd.focused_border_color = PRIMARY
        _fd.label_style = ft.TextStyle(color=_DK_MUTED, size=11)
        _fd.text_style  = ft.TextStyle(color=_DK_TEXT,  size=12)
    bank_search_tf.fill_color  = _DK_CARD2
    bank_search_tf.border_color = _DK_BORDER
    bank_search_tf.focused_border_color = PRIMARY
    bank_search_tf.label_style = ft.TextStyle(color=_DK_MUTED, size=11)
    bank_search_tf.text_style  = ft.TextStyle(color=_DK_TEXT,  size=12)

    # champs effectivité
    participation_field    = _tf("Participation %", 130, "0-100"); participation_field.value = "0"
    comprehension_field    = _tf("Comprehension %", 130, "0-100"); comprehension_field.value = "0"
    facilitator_rating     = _tf("Note facilitateur", 130, "0-100"); facilitator_rating.value = "0"
    session_quality_field  = _tf("Qualite session", 130, "0-100"); session_quality_field.value = "0"
    effectiveness_comments = _tf("Commentaires evaluation", multiline=True, min_lines=2)

    monthly_facilitator_field = _dd("Facilitateur du mois", 260, _facilitator_opts(), DEFAULT_TOOLBOX_FACILITATOR)

    # champs campagnes
    camp_name_field   = _tf("Nom de la campagne")
    camp_code_field   = _tf("Code campagne", 150)
    camp_desc_field   = _tf("Description", multiline=True, min_lines=2, max_lines=3)
    camp_category     = _dd("Categorie", 200, [ft.dropdown.Option(v,v) for v in bank_options["categories"]], "HSE General")
    camp_start_field  = _tf("Date debut", 150, "AAAA-MM-JJ")
    camp_end_field    = _tf("Date fin", 150, "AAAA-MM-JJ")
    camp_status_field = _dd("Statut", 160, [
        ft.dropdown.Option("planifiee","Planifiee"), ft.dropdown.Option("active","Active"),
        ft.dropdown.Option("terminee","Terminee"), ft.dropdown.Option("annulee","Annulee"),
    ], "planifiee")
    camp_site_field   = _dd("Site", 190,
        [ft.dropdown.Option("","Tous")] + [ft.dropdown.Option(str(r["value"]),str(r["label"])) for r in bank_options["sites"]])

    # ── notifications ─────────────────────────────────────────────────────────
    def notify(msg: str, color: str = MUTED) -> None:
        status_txt.value = msg
        status_txt.color = color
        show_feedback(page, msg, color)

    def _upd() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def _load_theme_opts() -> None:
        nonlocal options
        options = get_toolbox_options()
        state["themes"] = list_theme_catalog()
        topic_field.options = [ft.dropdown.Option(str(r["theme"]),str(r["theme"])) for r in state["themes"]]
        for fld in (facilitator_field, monthly_facilitator_field):
            fld.options = _facilitator_opts(str(fld.value or DEFAULT_TOOLBOX_FACILITATOR))
            fld.value   = str(fld.value or DEFAULT_TOOLBOX_FACILITATOR)

    def refresh(event: ft.ControlEvent | None = None) -> None:
        try:
            _load_theme_opts()
            state["data"]     = list_toolbox_topics(month_field.value)
            state["snapshot"] = get_toolbox_dashboard_snapshot(month_field.value)
            render()
            notify("Actualise.", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _upd()

    def _filtered_rows() -> list[dict[str, Any]]:
        data = state.get("data") or {"rows": []}
        sel  = str(status_filter.value or "all")
        return [r for r in data["rows"] if sel == "all" or r["status"] == sel]

    def _filtered_bank_themes_list(themes_all: list[dict[str, Any]]) -> list[dict[str, Any]]:
        search = str(bank_search_tf.value or "").strip().lower()
        cat    = str(bank_cat_filter.value or "")
        risk   = str(bank_risk_filter.value or "")
        freq   = str(bank_freq_filter.value or "")
        stat   = str(bank_stat_filter.value or "")
        site   = str(bank_site_filter.value or "")
        result = []
        for t in themes_all:
            if search:
                haystack = " ".join([
                    str(t.get("topic_en") or ""), str(t.get("theme_fr") or ""),
                    str(t.get("code_theme") or ""), str(t.get("category") or ""),
                ]).lower()
                if search not in haystack:
                    continue
            if cat and t.get("category") != cat:
                continue
            if risk and t.get("risk_level") != risk:
                continue
            if freq and t.get("frequency") != freq:
                continue
            if stat and t.get("status") != stat:
                continue
            if site and str(t.get("site_id") or "") != site:
                continue
            result.append(t)
        return result

    def _reset_bank_filters() -> None:
        bank_search_tf.value    = ""
        bank_cat_filter.value   = ""
        bank_risk_filter.value  = ""
        bank_freq_filter.value  = ""
        bank_stat_filter.value  = ""
        bank_site_filter.value  = ""
        render_bank()
        _upd()

    def _is_weekend(date_str: str) -> bool:
        from datetime import datetime
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").weekday() >= 5
        except ValueError:
            return False

    # ── actions planning ──────────────────────────────────────────────────────
    def do_preview_plan(event: ft.ControlEvent | None = None) -> None:
        try:
            result = preview_intelligent_toolbox_planning(
                month=month_field.value,
                facilitator=str(monthly_facilitator_field.value or "") or None,
                site_id=str(site_field.value or "") or None,
                skip_weekends=bool(state.get("skip_weekends", True)),
            )
            state["preview_result"] = result
            render_preview(result)
            preview_area.visible = True
            notify(f"Apercu : {result['new_assignments']} affectation(s) proposee(s). Confirme pour appliquer.", PRIMARY)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _upd()

    def do_apply_confirmed_plan(event: ft.ControlEvent | None = None) -> None:
        try:
            result = generate_intelligent_toolbox_planning(
                month=month_field.value,
                facilitator=str(monthly_facilitator_field.value or "") or None,
                site_id=str(site_field.value or "") or None,
            )
            state["preview_result"] = None
            preview_area.visible = False
            notify(f"Plan applique : {result['assigned']} jour(s) affecte(s), {result['remaining']} restant(s).", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    def cancel_preview(event: ft.ControlEvent | None = None) -> None:
        state["preview_result"] = None
        preview_area.visible = False
        notify("Apercu annule.", MUTED)
        _upd()

    def do_random_plan(event: ft.ControlEvent | None = None) -> None:
        try:
            count = assign_monthly_topics(month_field.value, monthly_facilitator_field.value)
            notify(f"{count} topic(s) affecte(s) aleatoirement.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    def do_apply_facilitator(event: ft.ControlEvent | None = None) -> None:
        try:
            count = apply_monthly_toolbox_facilitator(month_field.value, monthly_facilitator_field.value)
            notify(f"Facilitateur applique sur {count} jour(s).", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    def do_clear_month(event: ft.ControlEvent | None = None) -> None:
        try:
            count = clear_monthly_toolbox_topics(str(month_field.value or ""))
            state["selected_dates"] = set()
            notify(f"{count} theme(s) dissocie(s).", WARNING)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    # ── actions réalisation ───────────────────────────────────────────────────
    def start_edit(row: dict[str, Any]) -> None:
        state["editing_date"] = row["date_theme"]
        date_field.value = row["date_theme"]
        topic_field.value = str(row.get("theme") or "")
        facilitator_field.options = _facilitator_opts(str(row.get("facilitateur") or DEFAULT_TOOLBOX_FACILITATOR))
        facilitator_field.value   = str(row.get("facilitateur") or DEFAULT_TOOLBOX_FACILITATOR)
        site_field.value = str(row.get("site_id") or "")
        conf = (state.get("snapshot") or {}).get("confirmations") or []
        confirmed = next((c for c in conf if str(c.get("date_theme")) == row["date_theme"]), None)
        attendees_field.value = str(confirmed.get("attendees_count", 0)) if confirmed else "0"
        comments_field.value  = str(confirmed.get("comments") or "") if confirmed else ""
        notify(f"Edition du {row['date_theme']}.", PRIMARY)
        switch_tab("realization")
        _upd()

    def clear_form(event: ft.ControlEvent | None = None) -> None:
        state["editing_date"] = None
        state["selected_dates"] = set()
        date_field.value = ""
        topic_field.value = ""
        facilitator_field.value = DEFAULT_TOOLBOX_FACILITATOR
        site_field.value = ""
        attendees_field.value = "0"
        comments_field.value = ""
        notify("Formulaire vide.", MUTED)
        _upd()

    def save_topic(event: ft.ControlEvent | None = None) -> None:
        try:
            save_toolbox_topic({
                "date_theme": date_field.value, "theme": topic_field.value,
                "facilitateur": facilitator_field.value, "site_id": site_field.value,
            })
            notify("Theme enregistre.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    def save_confirmation(event: ft.ControlEvent | None = None) -> None:
        try:
            dates = [d.strip() for d in str(date_field.value or "").split(",") if d.strip()]
            if not dates:
                notify("Selectionne au moins une date.", DANGER)
                _upd()
                return
            for d in dates:
                save_desktop_confirmation({
                    "date_theme": d, "attendees_count": attendees_field.value,
                    "comments": comments_field.value, "facilitateur": facilitator_field.value,
                    "site_id": site_field.value,
                })
            notify(f"Realisation confirmee pour {len(dates)} jour(s) — {attendees_field.value} participant(s).", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    def delete_confirmation(date_str: str) -> None:
        try:
            delete_desktop_confirmation(date_str)
            notify("Confirmation supprimee.", WARNING)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    def assign_selected(event: ft.ControlEvent | None = None) -> None:
        try:
            dates = sorted(state.get("selected_dates") or [])
            count = assign_topic_to_dates({
                "dates": dates, "theme": topic_field.value,
                "facilitateur": facilitator_field.value, "site_id": site_field.value,
            })
            notify(f"{count} date(s) mises a jour.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    def delete_topic(row: dict[str, Any]) -> None:
        try:
            delete_toolbox_topic(str(row["date_theme"]))
            notify("Theme supprime.", WARNING)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    def toggle_date(row: dict[str, Any], selected: bool | None) -> None:
        dates: set[str] = set(state.get("selected_dates") or set())
        cur = str(row["date_theme"])
        if selected:
            dates.add(cur)
        else:
            dates.discard(cur)
        state["selected_dates"] = dates
        date_field.value = ", ".join(sorted(dates)) if dates else str(state.get("editing_date") or "")
        notify(f"{len(dates)} date(s) selectionnee(s).", PRIMARY if dates else MUTED)
        render()
        _upd()

    def export_attendance(date_str: str) -> None:
        try:
            out = export_session_attendance_xlsx(date_str)
            notify(f"Fiche de presence exportee : {out}", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        _upd()

    def export_excel(event: ft.ControlEvent | None = None) -> None:
        try:
            out = export_toolbox_talk_xlsx(str(month_field.value or ""))
            notify(f"Export cree : {out}", SUCCESS)
        except ValueError as exc:
            notify(str(exc), DANGER)
        _upd()

    # ── actions banque ────────────────────────────────────────────────────────
    def save_pro_theme(event: ft.ControlEvent | None = None) -> None:
        try:
            save_professional_toolbox_theme({
                "id_topic": state.get("editing_topic_id"),
                "topic_en": topic_en_field.value, "theme_fr": theme_fr_field.value,
                "category": category_field.value, "risk_level": risk_level_field.value,
                "frequency": frequency_field.value, "status": theme_status_field.value,
                "site_id": pro_site_field.value or None, "obligatoire": bool(pro_obligatoire.value),
            })
            _reset_pro_form()
            state["bank_form_visible"] = False
            notify("Theme professionnel enregistre.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    def _reset_pro_form() -> None:
        state["editing_topic_id"] = None
        topic_en_field.value = ""; theme_fr_field.value = ""
        category_field.value = "HSE General"; risk_level_field.value = "moyen"
        frequency_field.value = "mensuelle"; theme_status_field.value = "actif"
        pro_site_field.value = ""; pro_obligatoire.value = False

    def cancel_bank_edit(event: ft.ControlEvent | None = None) -> None:
        _reset_pro_form()
        state["bank_form_visible"] = False
        notify("Edition annulee.", MUTED)
        render()
        _upd()

    def edit_bank_theme(row: dict[str, Any]) -> None:
        state["editing_topic_id"] = int(row["id_topic"])
        state["bank_form_visible"] = True
        topic_en_field.value   = str(row.get("topic_en") or "")
        theme_fr_field.value   = str(row.get("theme_fr") or "")
        category_field.value   = str(row.get("category") or "HSE General")
        risk_level_field.value = str(row.get("risk_level") or "moyen")
        frequency_field.value  = str(row.get("frequency") or "mensuelle")
        theme_status_field.value = str(row.get("status") or "actif")
        pro_site_field.value   = str(row.get("site_id") or "")
        pro_obligatoire.value  = bool(row.get("obligatoire"))
        notify("Theme charge pour modification.", PRIMARY)
        switch_tab("bank")
        render_bank()
        _upd()

    def delete_bank_theme(row: dict[str, Any]) -> None:
        try:
            delete_theme_catalog(int(row["id_topic"]))
            if state.get("editing_topic_id") == int(row["id_topic"]):
                _reset_pro_form()
            notify("Theme supprime.", WARNING)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    def generate_catalog(event: ft.ControlEvent | None = None) -> None:
        try:
            count = generate_toolbox_theme_catalog(int(generated_count_field.value or 12))
            notify(f"{count} theme(s) OREZONE ajoutes.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    def suggest_ai_theme(event: ft.ControlEvent | None = None) -> None:
        try:
            data    = state.get("data") or {"rows": []}
            existing = [str(r.get("theme") or "") for r in data.get("rows", []) if r.get("theme")]
            catalog  = [str(r.get("theme") or "") for r in state.get("themes", []) if r.get("theme")]
            topic_en_field.value = "Generation IA en cours..."
            _upd()
            raw = suggest_toolbox_theme({
                "month": month_field.value, "site_id": site_field.value,
                "existing_month_topics": existing, "catalog_topics": catalog,
                "format": "English topic / Theme francais",
            }).strip()
            if " / " in raw:
                en_part, fr_part = raw.split(" / ", 1)
                topic_en_field.value = en_part.strip()
                theme_fr_field.value = fr_part.strip()
            else:
                topic_en_field.value = raw
            notify("Theme IA propose. Verifie et enregistre.", SUCCESS)
        except (ValueError, AIConfigurationError) as exc:
            topic_en_field.value = ""
            notify(str(exc), DANGER)
        _upd()

    # ── actions effectivité ───────────────────────────────────────────────────
    def save_effectiveness(usage_id: int, event: ft.ControlEvent | None = None) -> None:
        try:
            save_toolbox_effectiveness({
                "usage_id": usage_id, "participation_rate": participation_field.value,
                "comprehension_score": comprehension_field.value, "facilitator_rating": facilitator_rating.value,
                "session_quality": session_quality_field.value, "comments": effectiveness_comments.value,
                "evaluated_by": "desktop",
            })
            effectiveness_comments.value = ""
            notify("Evaluation d'effectivite enregistree.", SUCCESS)
            refresh()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    # ── actions campagnes ─────────────────────────────────────────────────────
    def save_campaign(event: ft.ControlEvent | None = None) -> None:
        try:
            save_toolbox_campaign({
                "id_campaign": state.get("editing_campaign_id"),
                "name": camp_name_field.value, "code_campaign": camp_code_field.value,
                "description": camp_desc_field.value, "category": camp_category.value,
                "start_date": camp_start_field.value, "end_date": camp_end_field.value,
                "status": camp_status_field.value, "site_id": camp_site_field.value or None,
                "topic_ids": [],
            })
            _reset_campaign_form()
            notify("Campagne enregistree.", SUCCESS)
            render_campaigns()
            _upd()
        except ValueError as exc:
            notify(str(exc), DANGER)
            _upd()

    def _reset_campaign_form() -> None:
        state["editing_campaign_id"] = None
        camp_name_field.value = ""; camp_code_field.value = ""; camp_desc_field.value = ""
        camp_category.value = "HSE General"; camp_start_field.value = ""; camp_end_field.value = ""
        camp_status_field.value = "planifiee"; camp_site_field.value = ""

    def edit_campaign(row: dict[str, Any]) -> None:
        state["editing_campaign_id"] = int(row["id_campaign"])
        camp_name_field.value   = str(row.get("name") or "")
        camp_code_field.value   = str(row.get("code_campaign") or "")
        camp_desc_field.value   = str(row.get("description") or "")
        camp_category.value     = str(row.get("category") or "HSE General")
        camp_start_field.value  = str(row.get("start_date") or "")
        camp_end_field.value    = str(row.get("end_date") or "")
        camp_status_field.value = str(row.get("status") or "planifiee")
        camp_site_field.value   = str(row.get("site_id") or "")
        notify("Campagne chargee pour modification.", PRIMARY)
        switch_tab("campaigns")
        _upd()

    # ── RENDER PREVIEW PLAN ───────────────────────────────────────────────────
    def render_preview(result: dict[str, Any]) -> None:
        rows = result.get("preview") or []
        if not rows:
            preview_area.controls = [ft.Text("Aucun jour disponible pour la planification.", color=MUTED)]
            return
        preview_area.controls = [_panel(
            f"Apercu plan intelligent — {result['new_assignments']} nouvelles affectations"
            f" (deja planifie : {result['already_planned']})",
            ft.Icons.PREVIEW_OUTLINED, WARNING, [
                ft.Text(
                    "Verifie ce plan avant d'appliquer. Scores : risque + obligatoire + campagne + frequence + categories + effectivite.",
                    size=12, color=MUTED),
                ft.Row(controls=[
                    _primary_btn("Appliquer ce plan", ft.Icons.CHECK_CIRCLE_OUTLINED, do_apply_confirmed_plan),
                    _danger_btn("Annuler l'apercu", ft.Icons.CLOSE_OUTLINED, cancel_preview),
                ], spacing=10),
                ft.Container(
                    bgcolor=_W, border=ft.border.all(1, _ABD), border_radius=10, padding=0,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    content=ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                        professional_data_table(
                            columns=[
                                ft.DataColumn(ft.Text("Date",      weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("J",         weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Topic EN / Theme FR", weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Categorie", weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Risque",    weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Score",     weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Oblig.",    weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Campagne",  weight=ft.FontWeight.BOLD)),
                            ],
                            rows=[ft.DataRow(cells=[
                                ft.DataCell(ft.Text(str(r["date_theme"]), weight=ft.FontWeight.W_500)),
                                ft.DataCell(ft.Text(str(r.get("weekday","-")), color=MUTED, size=11)),
                                ft.DataCell(ft.Text(f"{r.get('topic_en','')} / {r.get('theme_fr','')}",
                                    width=300, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)),
                                ft.DataCell(_mini_badge(str(r.get("category","-")), PRIMARY)),
                                ft.DataCell(_risk_badge(str(r.get("risk_level","moyen")))),
                                ft.DataCell(_score_bar(float(r.get("priority_score",0)))),
                                ft.DataCell(ft.Icon(
                                    ft.Icons.CHECK_CIRCLE_OUTLINED if r.get("obligatoire") else ft.Icons.RADIO_BUTTON_UNCHECKED,
                                    color=SUCCESS if r.get("obligatoire") else MUTED, size=16)),
                                ft.DataCell(ft.Icon(
                                    ft.Icons.CAMPAIGN_OUTLINED if r.get("active_campaign") else ft.Icons.REMOVE,
                                    color=WARNING if r.get("active_campaign") else MUTED, size=16)),
                            ]) for r in rows],
                            border=None, border_radius=0, heading_row_color=_ASF,
                        )
                    ]),
                ),
            ],
        )]

    # ── RENDER DASHBOARD ──────────────────────────────────────────────────────
    def render_dashboard() -> None:
        snap      = state.get("snapshot") or {}
        analytics = snap.get("analytics") or {}
        faci      = snap.get("facilitators") or {}
        recent    = (snap.get("history") or [])[:6]

        try:
            today_info = get_today_toolbox_session()
        except Exception:
            today_info = {}
        try:
            bank_alerts = get_toolbox_theme_bank_alerts(month_field.value)
        except Exception:
            bank_alerts = []
        try:
            bank_stats = get_toolbox_theme_bank_statistics(month_field.value)
        except Exception:
            bank_stats = {}
        try:
            trend = get_toolbox_trend_data(6)
        except Exception:
            trend = []
        try:
            conflicts = detect_facilitator_conflicts(month_field.value)
        except Exception:
            conflicts = []

        _build_today_banner(today_info)

        kpis = ft.ResponsiveRow(controls=[
            _kpi("Sessions planifiees",  analytics.get("planned",0),       PRIMARY, ft.Icons.CALENDAR_MONTH_OUTLINED),
            _kpi("Sessions realisees",   analytics.get("realized",0),      SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
            _kpi("Participants total",   analytics.get("participants",0),  PRIMARY, ft.Icons.GROUPS_OUTLINED),
            _kpi("Moy. / session",       analytics.get("average_participants",0), SUCCESS, ft.Icons.INSIGHTS_OUTLINED),
            _kpi("Sessions manquantes",  analytics.get("missing",0),       DANGER,  ft.Icons.REPORT_PROBLEM_OUTLINED),
            _kpi("Taux planning",        f"{analytics.get('planning_rate',0)}%", WARNING, ft.Icons.QUERY_STATS_OUTLINED),
            _kpi("Themes banque",        bank_stats.get("total",0),        _PRP,    ft.Icons.ACCOUNT_BALANCE_OUTLINED),
            _kpi("Efficacite moy.",      f"{bank_stats.get('average_effectiveness',0):.1f}/100", _TEAL, ft.Icons.STAR_OUTLINED),
        ], spacing=12, run_spacing=12)

        prog_panel = _panel("Progression mensuelle", ft.Icons.TRENDING_UP_OUTLINED, PRIMARY, [
            _progress_bar("Planning complete",  analytics.get("planning_rate",0),  PRIMARY),
            _progress_bar("Sessions realisees", analytics.get("realization_rate",0), SUCCESS),
            _progress_bar("Participation moy.", min(round(float(analytics.get("average_participants",0))*4),100), WARNING),
        ])

        faci_panel = _panel("Top facilitateurs", ft.Icons.PERSON_PIN_OUTLINED, SUCCESS, [
            _metric_bar(n, c, max(sum(faci.values()),1), SUCCESS) for n, c in list(faci.items())[:5]
        ] or [ft.Text("Aucune session realisee.", color=MUTED, size=12)])

        trend_panel = _build_trend_panel(trend)

        recent_panel = _panel("Sessions recentes", ft.Icons.HISTORY_OUTLINED, MUTED, [
            _session_row(str(r.get("date_theme","-")), str(r.get("theme","-")),
                         int(r.get("attendees_count",0)), bool(r.get("realized")))
            for r in recent
        ] or [ft.Text("Aucune session.", color=MUTED, size=12)])

        alert_ctrls: list[ft.Control] = []
        for al in bank_alerts[:6]:
            clr = DANGER if al["level"] == "Critique" else WARNING
            alert_ctrls.append(ft.Container(
                bgcolor=_soft_bg(clr), border=ft.border.all(1, _soft_bdr(clr)),
                border_radius=8, padding=ft.padding.symmetric(horizontal=10, vertical=7),
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED, color=clr, size=15),
                    ft.Text(f"[{al['code_theme']}] {al['message']}", color=TEXT, size=11, expand=True),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))
        alert_panel = _panel("Alertes qualite banque", ft.Icons.AUTO_AWESOME_OUTLINED, DANGER,
            alert_ctrls or [ft.Row(controls=[
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED, color=SUCCESS, size=18),
                ft.Text("Aucune alerte qualite.", color=SUCCESS, size=12),
            ], spacing=8)])

        conflict_ctrls: list[ft.Control] = []
        for c in conflicts[:5]:
            conflict_ctrls.append(ft.Container(
                bgcolor=_RSF, border=ft.border.all(1, _RBD), border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=7),
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.PERSON_OFF_OUTLINED, color=DANGER, size=15),
                    ft.Column(controls=[
                        ft.Text(f"{c['date_theme']} — {c['facilitateur']}", size=11,
                                weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text(f"Sites : {c['sites']}", size=11, color=MUTED),
                    ], spacing=1, expand=True),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))
        conflict_panel = _panel("Conflits facilitateur", ft.Icons.PERSON_OFF_OUTLINED, DANGER,
            conflict_ctrls or [ft.Row(controls=[
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED, color=SUCCESS, size=18),
                ft.Text("Aucun conflit detecte ce mois.", color=SUCCESS, size=12),
            ], spacing=8)])

        dashboard_area.controls = [
            kpis,
            ft.ResponsiveRow(controls=[
                ft.Container(col={"xs":12,"lg":5}, content=prog_panel),
                ft.Container(col={"xs":12,"lg":7}, content=faci_panel),
            ], spacing=12, run_spacing=12),
            trend_panel,
            ft.ResponsiveRow(controls=[
                ft.Container(col={"xs":12,"lg":7}, content=recent_panel),
                ft.Container(col={"xs":12,"lg":5}, content=alert_panel),
            ], spacing=12, run_spacing=12),
            conflict_panel,
        ]

    def _build_today_banner(info: dict[str, Any]) -> None:
        if not info:
            today_banner.visible = False
            return
        has_topic = bool(info.get("has_topic"))
        confirmed = bool(info.get("confirmed"))
        attendees = int(info.get("attendees") or 0)
        topic     = info.get("topic") or {}
        theme     = str(topic.get("theme") or "Aucun theme programme")
        topic_en  = theme.split(" / ")[0] if " / " in theme else theme
        theme_fr  = theme.split(" / ")[1] if " / " in theme else ""
        faci      = str(topic.get("facilitateur") or "—")

        if confirmed:
            color, icon, bg, bdr, lbl = SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINED, _GSF, _GBD, f"Confirme — {attendees} participant(s)"
        elif has_topic:
            color, icon, bg, bdr, lbl = PRIMARY, ft.Icons.TODAY_OUTLINED, _BSF, _BBD, "Non confirme — session en attente"
        else:
            color, icon, bg, bdr, lbl = WARNING, ft.Icons.EVENT_BUSY_OUTLINED, _ASF, _ABD, "Aucun theme programme aujourd'hui"

        today_banner.controls = [ft.Container(
            bgcolor=bg, border=ft.border.all(1, bdr), border_radius=12,
            margin=ft.margin.only(bottom=4),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            content=ft.Row(controls=[
                ft.Container(width=42, height=42, bgcolor=_soft_bg(color), border_radius=10,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(icon, color=color, size=22)),
                ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Text(f"AUJOURD'HUI — {info.get('date','-')} ({info.get('weekday','')})",
                                size=11, weight=ft.FontWeight.BOLD, color=color),
                        ft.Container(bgcolor=_soft_bg(color), border_radius=20,
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            content=ft.Text(lbl, size=10, color=color, weight=ft.FontWeight.W_500)),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(topic_en, size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                    ft.Text(theme_fr, size=11, color=MUTED) if theme_fr else ft.Container(height=0),
                    ft.Text(f"Facilitateur : {faci}", size=11, color=MUTED),
                ], spacing=2, expand=True),
                ft.Row(controls=[
                    _icon_btn(ft.Icons.FACT_CHECK_OUTLINED, "Confirmer cette session",
                              lambda e: (setattr(date_field, "value", info.get("date","")),
                                         switch_tab("realization"), _upd()), SUCCESS),
                    _icon_btn(ft.Icons.PRINT_OUTLINED, "Fiche de presence",
                              lambda e: export_attendance(str(info.get("date",""))), _TEAL),
                ], spacing=4),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )]
        today_banner.visible = True

    def _build_trend_panel(trend: list[dict[str, Any]]) -> ft.Control:
        if not trend:
            return ft.Container()
        max_planned = max((r["planned"] for r in trend), default=1) or 1
        bars = []
        for r in trend:
            plan_h = max(4, round(r["planned"] * 80 / max_planned))
            real_h = max(0, round(r["realized"] * 80 / max_planned))
            bars.append(ft.Column(controls=[
                ft.Text(f"{r.get('completion_rate',0)}%", size=9, color=MUTED,
                        text_align=ft.TextAlign.CENTER),
                ft.Stack(controls=[
                    ft.Container(width=28, height=plan_h, bgcolor=_BBD, border_radius=4,
                                 alignment=ft.Alignment(0, 1)),
                    ft.Container(width=18, height=real_h, bgcolor=SUCCESS, border_radius=3,
                                 alignment=ft.Alignment(0, 1)),
                ], width=28, height=plan_h),
                ft.Text(str(r.get("label","-")), size=9, color=MUTED, text_align=ft.TextAlign.CENTER),
            ], spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER))

        total_real = sum(r["realized"] for r in trend)
        total_part = sum(r["participants"] for r in trend)
        avg_part   = round(total_part / max(total_real, 1), 1)

        return _panel("Tendance 6 mois — planning vs realisation", ft.Icons.BAR_CHART_OUTLINED, PRIMARY, [
            ft.Row(controls=[
                ft.Container(width=12, height=12, bgcolor=_BBD, border_radius=2),
                ft.Text("Planifie", size=10, color=MUTED),
                ft.Container(width=12, height=12, bgcolor=SUCCESS, border_radius=2),
                ft.Text("Realise", size=10, color=MUTED),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row(controls=bars, spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
            ft.Divider(height=1),
            ft.Row(controls=[
                ft.Text(f"Sessions realisees (6 mois) : {total_real}", size=11, color=SUCCESS),
                ft.Text(f"Moy. participants/session : {avg_part}", size=11, color=MUTED),
            ], spacing=24),
        ])

    # ── RENDER PLANNING ───────────────────────────────────────────────────────
    def render_planning() -> None:
        data  = state.get("data") or {"rows":[], "label":""}
        rows  = data.get("rows") or []
        skip_wk = state.get("skip_weekends", True)
        done  = sum(1 for r in rows if r["status"]=="done")
        total = len(rows)

        mode_toggle = ft.Row(controls=[
            _tab_pill("Planification intelligente","intelligent",state.get("plan_mode","intelligent"),
                      lambda e: _set_plan_mode("intelligent")),
            _tab_pill("Affectation aleatoire","random",state.get("plan_mode","intelligent"),
                      lambda e: _set_plan_mode("random")),
        ], spacing=6)

        if state.get("plan_mode") == "intelligent":
            desc = ("La planification intelligente priorise : themes critiques (+70), obligatoires (+55), "
                    "campagnes actives (+45), frequence (+40), couverture categories (+25), effectivite (+12). "
                    "Utilise l'Apercu pour voir le plan AVANT d'appliquer.")
            action_btn = _outline_btn("Apercu du plan", ft.Icons.PREVIEW_OUTLINED, do_preview_plan)
            apply_btn  = _primary_btn("Appliquer directement", ft.Icons.AUTO_AWESOME_OUTLINED, do_apply_confirmed_plan)
        else:
            desc = "L'affectation aleatoire distribue les themes de la banque en evitant les doublons mensuels."
            action_btn = _primary_btn("Affecter aleatoirement", ft.Icons.SHUFFLE_OUTLINED, do_random_plan)
            apply_btn  = ft.Container()

        weekend_check = ft.Checkbox(
            label="Ignorer les weekends",
            value=skip_wk,
            on_change=lambda e: _toggle_weekends(e.control.value),
        )

        auto_panel = _panel("Mode de planification", ft.Icons.SETTINGS_OUTLINED, PRIMARY, [
            ft.Text(desc, size=12, color=MUTED),
            mode_toggle,
            ft.Row(controls=[
                monthly_facilitator_field, weekend_check, action_btn, apply_btn,
                _outline_btn("Appliquer facilitateur", ft.Icons.PERSON_PIN_OUTLINED, do_apply_facilitator),
                _danger_btn("Dissocier le mois", ft.Icons.LINK_OFF_OUTLINED, do_clear_month),
            ], wrap=True, spacing=10),
        ])

        calendar_rows = [r for r in rows if not (skip_wk and _is_weekend(str(r.get("date_theme",""))))]
        calendar_panel = _panel(
            f"Calendrier — {data.get('label','-')}  ({done}/{total} renseignes)",
            ft.Icons.CALENDAR_VIEW_MONTH_OUTLINED,
            SUCCESS if done==total and total else WARNING,
            [ft.ResponsiveRow(controls=[_day_card(r) for r in calendar_rows], spacing=6, run_spacing=6)],
        )
        planning_area.controls = [auto_panel, preview_area, calendar_panel]

    def _set_plan_mode(mode: str) -> None:
        state["plan_mode"] = mode
        render_planning()
        _upd()

    def _toggle_weekends(val: bool) -> None:
        state["skip_weekends"] = val
        render_planning()
        _upd()

    # ── RENDER RÉALISATION ────────────────────────────────────────────────────
    def render_realization() -> None:
        rows     = _filtered_rows()
        snap     = state.get("snapshot") or {}
        confs    = {str(c.get("date_theme")): c for c in (snap.get("confirmations") or [])}
        selected = set(state.get("selected_dates") or set())

        form_panel = _panel("Saisie de realisation", ft.Icons.FACT_CHECK_OUTLINED, SUCCESS, [
            ft.Text("Selectionne une ou plusieurs dates dans le tableau puis renseigne la session.",
                    size=12, color=MUTED),
            ft.Row(controls=[date_field, topic_field, facilitator_field, site_field], wrap=True, spacing=10),
            ft.Row(controls=[
                attendees_field,
                ft.Column(controls=[
                    ft.Text("Participants", size=11, color=MUTED),
                    ft.Row(controls=[
                        ft.IconButton(ft.Icons.REMOVE, icon_color=DANGER, icon_size=16,
                                      on_click=lambda e: _adj_attendees(-1)),
                        ft.IconButton(ft.Icons.ADD, icon_color=SUCCESS, icon_size=16,
                                      on_click=lambda e: _adj_attendees(1)),
                    ], spacing=0),
                ], spacing=2),
                comments_field,
            ], wrap=True, spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Row(controls=[
                _primary_btn("Enregistrer theme", ft.Icons.SAVE_OUTLINED, save_topic),
                _primary_btn("Confirmer realisation", ft.Icons.VERIFIED_OUTLINED, save_confirmation),
                _outline_btn("Affecter dates selectionnees", ft.Icons.CHECKLIST_OUTLINED, assign_selected),
                _outline_btn("Effacer formulaire", ft.Icons.CLEAR_OUTLINED, clear_form),
            ], wrap=True, spacing=10),
        ])

        action_bar = ft.Container(
            bgcolor=_BSF, border=ft.border.all(1,_BBD), border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            content=ft.Row(controls=[
                ft.Row(controls=[
                    _icon_btn(ft.Icons.REFRESH_OUTLINED, "Actualiser", refresh, PRIMARY),
                    _icon_btn(ft.Icons.DOWNLOAD_OUTLINED, "Exporter rapport mensuel", export_excel, SUCCESS),
                    _icon_btn(ft.Icons.AUTO_AWESOME_OUTLINED, "Theme IA", suggest_ai_theme, WARNING),
                    _icon_btn(ft.Icons.CLEAR_OUTLINED, "Effacer formulaire", clear_form, MUTED),
                ], spacing=4),
                status_txt,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

        table = ft.Container(
            bgcolor=_W, border=ft.border.all(1,_BBD), border_radius=10, padding=0,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                professional_data_table(
                    columns=[
                        ft.DataColumn(ft.Text("Sel.",          weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Date",          weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Jour",          weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Topic EN / Theme FR", weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Facilitateur",  weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Etat",          weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Participants",  weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Actions",       weight=ft.FontWeight.BOLD)),
                    ],
                    rows=[ft.DataRow(cells=[
                        ft.DataCell(ft.Checkbox(
                            value=str(r["date_theme"]) in selected, active_color=PRIMARY,
                            on_change=lambda e, row=r: toggle_date(row, e.control.value))),
                        ft.DataCell(ft.Text(str(r["date_theme"]), weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(str(r["weekday"]), color=MUTED, size=12)),
                        ft.DataCell(ft.Text(str(r.get("theme") or "—"), width=300,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                            color=TEXT if r.get("theme") else MUTED, italic=not bool(r.get("theme")))),
                        ft.DataCell(ft.Text(str(r.get("facilitateur") or "—"), color=MUTED, size=12)),
                        ft.DataCell(_state_badge(str(r["status"]))),
                        ft.DataCell(_confirmed_cell(r["date_theme"], confs)),
                        ft.DataCell(ft.Row(controls=[
                            ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Modifier",
                                icon_color=PRIMARY, icon_size=18,
                                on_click=lambda e, row=r: start_edit(row)),
                            ft.IconButton(ft.Icons.PRINT_OUTLINED, tooltip="Fiche de presence",
                                icon_color=_TEAL, icon_size=18,
                                on_click=lambda e, row=r: export_attendance(str(row["date_theme"]))),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Supprimer theme",
                                icon_color=DANGER, icon_size=18,
                                disabled=not r.get("id_theme"),
                                on_click=lambda e, row=r: delete_topic(row)),
                        ], spacing=0)),
                    ]) for r in rows],
                    border=None, border_radius=0, heading_row_color=_BHD,
                )
            ]),
        )
        realization_area.controls = [form_panel, action_bar, table]

    def _adj_attendees(delta: int) -> None:
        try:
            attendees_field.value = str(max(0, int(attendees_field.value or 0) + delta))
        except ValueError:
            attendees_field.value = "0"
        _upd()

    def _confirmed_cell(date_str: str, confs: dict) -> ft.Control:
        conf = confs.get(str(date_str))
        if not conf:
            return ft.Text("—", color=MUTED, size=12)
        count   = int(conf.get("attendees_count") or 0)
        src     = str(conf.get("device_id") or "")
        src_clr = _TEAL if src == "DESKTOP" else PRIMARY
        return ft.Container(
            bgcolor=_GSF, border=ft.border.all(1,_GBD), border_radius=12,
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            content=ft.Row(controls=[
                ft.Icon(ft.Icons.GROUPS_OUTLINED, color=SUCCESS, size=14),
                ft.Text(str(count), color=SUCCESS, size=12, weight=ft.FontWeight.BOLD),
                ft.Container(bgcolor=_soft_bg(src_clr), border_radius=8,
                    padding=ft.padding.symmetric(horizontal=5, vertical=1),
                    content=ft.Text(src or "—", size=9, color=src_clr)),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, icon_size=14,
                    tooltip="Supprimer confirmation",
                    on_click=lambda e, d=date_str: delete_confirmation(d)),
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
        )

    # ── RENDER BANQUE ─────────────────────────────────────────────────────────
    def render_bank() -> None:
        is_editing = bool(state.get("editing_topic_id"))
        try:
            stats = get_toolbox_theme_bank_statistics(month_field.value)
        except Exception:
            stats = {}
        try:
            alerts_data = get_toolbox_theme_bank_alerts(month_field.value)
        except Exception:
            alerts_data = []
        try:
            themes_all = list_professional_toolbox_themes()
        except Exception:
            themes_all = []

        themes = _filtered_bank_themes_list(themes_all)

        # ── KPI Cards (dark) ────────────────────────────────────────────────
        stats_row = ft.ResponsiveRow(controls=[
            _kpi_dk_top("Themes actifs",     stats.get("active", 0),                SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
            _kpi_dk_top("Themes critiques",  stats.get("critical", 0),              DANGER,  ft.Icons.PRIORITY_HIGH_OUTLINED),
            _kpi_dk_top("Utilises (30j)",    stats.get("used_month", 0),            PRIMARY, ft.Icons.TODAY_OUTLINED),
            _kpi_dk_top("En attente",        stats.get("inactive", 0),              WARNING, ft.Icons.PENDING_OUTLINED),
            _kpi_dk_top("Taux couverture",   f"{stats.get('coverage_rate',0)}%",    SUCCESS, ft.Icons.INSIGHTS_OUTLINED),
            _kpi_dk_top("Efficacite moy.",   f"{stats.get('average_effectiveness',0):.0f}%", _PRP, ft.Icons.STAR_OUTLINED),
        ], spacing=10, run_spacing=10)

        # ── Action bar ──────────────────────────────────────────────────────
        action_bar = ft.Container(
            bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=12,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            content=ft.Row(controls=[
                ft.ElevatedButton(
                    "+ Nouveau theme", icon=ft.Icons.ADD_CIRCLE_OUTLINED,
                    style=ft.ButtonStyle(bgcolor=PRIMARY, color=_W, elevation=1,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=14, vertical=10)),
                    on_click=lambda e: (
                        _reset_pro_form(),
                        state.update({"bank_form_visible": True}),
                        render_bank(), _upd()
                    ),
                ),
                _dk_outline_btn("Importer Excel",         ft.Icons.UPLOAD_FILE_OUTLINED,  lambda e: None),
                _dk_outline_btn("Generation IA",          ft.Icons.AUTO_AWESOME_OUTLINED, suggest_ai_theme),
                _dk_outline_btn("Generation automatique", ft.Icons.LIBRARY_ADD_OUTLINED,  generate_catalog),
                _dk_outline_btn("Campagnes HSE",          ft.Icons.CAMPAIGN_OUTLINED,     lambda e: switch_tab("campaigns")),
                ft.OutlinedButton("Exporter", icon=ft.Icons.DOWNLOAD_OUTLINED,
                    on_click=export_excel,
                    style=ft.ButtonStyle(color=SUCCESS, side=ft.BorderSide(1, SUCCESS),
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=14, vertical=10))),
            ], spacing=8, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

        # ── Filter bar ──────────────────────────────────────────────────────
        count_badge = ft.Container(
            bgcolor=_DK_CARD2, border=ft.border.all(1, _DK_BORDER), border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            content=ft.Text(f"{len(themes)} / {len(themes_all)} themes",
                size=12, color=_DK_MUTED, weight=ft.FontWeight.W_500),
        )
        filter_bar = ft.Container(
            bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=12,
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SEARCH, color=_DK_MUTED, size=18),
                            bank_search_tf,
                            ft.Container(expand=True),
                            count_badge,
                        ],
                        spacing=8,
                        wrap=False,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            bank_cat_filter, bank_risk_filter, bank_freq_filter,
                            bank_stat_filter, bank_site_filter,
                            ft.IconButton(icon=ft.Icons.RESTART_ALT_OUTLINED, icon_color=_DK_MUTED,
                                tooltip="Reinitialiser les filtres",
                                on_click=lambda e: _reset_bank_filters()),
                        ],
                        spacing=8,
                        wrap=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=6,
                tight=True,
            ),
        )

        # ── Formulaire ajout / edition ──────────────────────────────────────
        form_title_icon = ft.Icons.EDIT_NOTE_OUTLINED if is_editing else ft.Icons.ADD_BOX_OUTLINED
        form_accent     = WARNING if is_editing else PRIMARY
        form_panel_inner = _panel_dk(
            "Modifier le theme" if is_editing else "Ajouter un theme professionnel",
            form_title_icon, form_accent, [
                ft.Row(controls=[topic_en_field, theme_fr_field], wrap=True, spacing=10),
                ft.Row(controls=[category_field, risk_level_field, frequency_field,
                                  theme_status_field, pro_site_field, pro_obligatoire],
                       wrap=True, spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row(controls=[
                    _primary_btn("Modifier" if is_editing else "Ajouter", ft.Icons.SAVE_OUTLINED, save_pro_theme),
                    ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE_OUTLINED, visible=is_editing,
                        style=ft.ButtonStyle(color=DANGER, side=ft.BorderSide(1, DANGER),
                                             shape=ft.RoundedRectangleBorder(radius=8)),
                        on_click=cancel_bank_edit),
                    ft.VerticalDivider(width=10),
                    generated_count_field,
                    _dk_outline_btn("Theme IA", ft.Icons.AUTO_AWESOME_OUTLINED, suggest_ai_theme),
                    _dk_outline_btn("Generer themes OREZONE", ft.Icons.LIBRARY_ADD_OUTLINED, generate_catalog),
                ], wrap=True, spacing=10),
            ],
        )
        form_panel = ft.Container(
            content=form_panel_inner,
            visible=state.get("bank_form_visible", False),
        )

        # ── Sidebar : repartitions + alertes ────────────────────────────────
        cat_counts: dict[str, int] = {}
        for t in themes_all:
            k = str(t.get("category") or "Autre")
            cat_counts[k] = cat_counts.get(k, 0) + 1
        total_all   = len(themes_all) or 1
        cat_palette = [PRIMARY, DANGER, WARNING, SUCCESS, _PRP, _TEAL, "#F43F5E", "#0EA5E9", "#84CC16"]
        cat_items   = sorted(cat_counts.items(), key=lambda x: -x[1])

        risk_labels = [("critique","Critique"), ("eleve","Eleve"), ("moyen","Moyen"), ("faible","Faible")]
        risk_colors = {"critique":DANGER, "eleve":WARNING, "moyen":PRIMARY, "faible":SUCCESS}
        risk_counts: dict[str, int] = {"critique":0, "eleve":0, "moyen":0, "faible":0}
        for t in themes_all:
            rk = str(t.get("risk_level") or "moyen")
            if rk in risk_counts:
                risk_counts[rk] += 1
        max_risk = max(risk_counts.values(), default=1) or 1

        sidebar = ft.Column(controls=[
            _panel_dk("Repartition par categorie", ft.Icons.DONUT_LARGE_OUTLINED, PRIMARY, [
                *[
                    ft.Row(controls=[
                        ft.Container(width=10, height=10,
                                     bgcolor=cat_palette[i % len(cat_palette)],
                                     border_radius=5),
                        ft.Text(cat, size=11, color=_DK_TEXT, expand=True, max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{cnt} ({round(cnt*100/total_all)}%)",
                                size=10, color=_DK_MUTED),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                    for i, (cat, cnt) in enumerate(cat_items[:7])
                ],
                ft.Text(f"Total : {total_all} themes", size=10,
                        color=_DK_MUTED, weight=ft.FontWeight.W_600),
            ]),
            _panel_dk("Repartition par niveau de risque", ft.Icons.WARNING_AMBER_OUTLINED, WARNING, [
                *[
                    ft.Column(controls=[
                        ft.Row(controls=[
                            ft.Text(label, size=11, color=_DK_TEXT, expand=True),
                            ft.Text(f"{risk_counts[key]}  ({round(risk_counts[key]*100/total_all)}%)",
                                    size=10, color=risk_colors[key], weight=ft.FontWeight.BOLD),
                        ]),
                        ft.ProgressBar(value=risk_counts[key]/max_risk, color=risk_colors[key],
                                       bgcolor=_DK_TRACK, height=6, border_radius=3),
                    ], spacing=3)
                    for key, label in risk_labels
                ],
            ]),
            _panel_dk("Alertes & recommandations", ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, DANGER, [
                *(
                    [
                        ft.Container(
                            bgcolor="#380A0A" if al["level"]=="Critique" else "#2D1600",
                            border=ft.border.all(1, DANGER if al["level"]=="Critique" else WARNING),
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=10, vertical=7),
                            content=ft.Row(controls=[
                                ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED,
                                        color=DANGER if al["level"]=="Critique" else WARNING,
                                        size=14),
                                ft.Column(controls=[
                                    ft.Text(f"[{al['code_theme']}] {al['theme']}", size=10,
                                            color=_DK_TEXT, weight=ft.FontWeight.BOLD, max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(al["message"], size=10, color=_DK_MUTED, max_lines=2),
                                ], spacing=1, expand=True),
                            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        )
                        for al in alerts_data[:5]
                    ]
                    if alerts_data else [
                        ft.Row(controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED, color=SUCCESS, size=16),
                            ft.Text("Aucune alerte qualite.", color=SUCCESS, size=11),
                        ], spacing=8)
                    ]
                ),
            ]),
        ], spacing=12, width=295)

        # ── Table principale ────────────────────────────────────────────────
        table_ctrl = _bank_table_dk(themes, edit_bank_theme, delete_bank_theme)

        # ── Split : table (expand) + sidebar (largeur fixe) ─────────────────
        main_split = ft.Row(
            controls=[
                ft.Column(controls=[table_ctrl], expand=True, spacing=0),
                sidebar,
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # ── Footer : 4 panneaux info ─────────────────────────────────────────
        freq_colors_map = {"quotidienne":SUCCESS, "hebdomadaire":PRIMARY, "mensuelle":WARNING,
                           "trimestrielle":DANGER, "semestrielle":_PRP, "annuelle":_TEAL}
        freq_hints_map  = {"quotidienne":"Chaque jour", "hebdomadaire":"Chaque semaine",
                           "mensuelle":"Chaque mois", "trimestrielle":"Tous les 3 mois",
                           "semestrielle":"Tous les 6 mois", "annuelle":"Chaque annee"}
        freq_items: list[ft.Control] = []
        for freq in bank_options.get("frequencies", []):
            clr = freq_colors_map.get(freq, PRIMARY)
            freq_items.append(ft.Row(controls=[
                ft.Container(width=8, height=8, bgcolor=clr, border_radius=4),
                ft.Column(controls=[
                    ft.Text(freq.title(), size=11, color=_DK_TEXT, weight=ft.FontWeight.W_600),
                    ft.Text(freq_hints_map.get(freq, ""), size=9, color=_DK_MUTED),
                ], spacing=0),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER))

        actif_cnt    = sum(1 for t in themes_all if str(t.get("status")) == "actif")
        attente_cnt  = sum(1 for t in themes_all if str(t.get("status")) == "en_attente")
        inactif_cnt  = sum(1 for t in themes_all if str(t.get("status")) == "inactif")
        obsolete_cnt = sum(1 for t in themes_all if str(t.get("status")) == "obsolete")

        footer = ft.ResponsiveRow(controls=[
            ft.Container(col={"xs":12,"sm":6,"lg":3}, content=_panel_dk(
                "Frequences disponibles", ft.Icons.SCHEDULE_OUTLINED, _TEAL, freq_items)),
            ft.Container(col={"xs":12,"sm":6,"lg":3}, content=_panel_dk(
                "Statut des themes", ft.Icons.FACT_CHECK_OUTLINED, SUCCESS, [
                    _dk_stat_row("Actif",      actif_cnt,    SUCCESS),
                    _dk_stat_row("En attente", attente_cnt,  WARNING),
                    _dk_stat_row("Inactif",    inactif_cnt,  MUTED),
                    _dk_stat_row("Obsolete",   obsolete_cnt, DANGER),
                ])),
            ft.Container(col={"xs":12,"sm":6,"lg":3}, content=_panel_dk(
                "Generation automatique intelligente", ft.Icons.AUTO_AWESOME_OUTLINED, _PRP, [
                    ft.Column(controls=[
                        ft.Row(controls=[ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED, color=SUCCESS, size=13),
                            ft.Text("Evite les repetitions du mois", size=11, color=_DK_TEXT)], spacing=6),
                        ft.Row(controls=[ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED, color=SUCCESS, size=13),
                            ft.Text("Priorise les themes critiques", size=11, color=_DK_TEXT)], spacing=6),
                        ft.Row(controls=[ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED, color=SUCCESS, size=13),
                            ft.Text("Respecte les frequences definies", size=11, color=_DK_TEXT)], spacing=6),
                        ft.Row(controls=[ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED, color=SUCCESS, size=13),
                            ft.Text("Aligne sur les campagnes HSE", size=11, color=_DK_TEXT)], spacing=6),
                    ], spacing=6),
                    ft.ElevatedButton("Lancer la generation automatique",
                        icon=ft.Icons.PLAY_CIRCLE_OUTLINED, on_click=generate_catalog,
                        style=ft.ButtonStyle(bgcolor=_PRP, color=_W,
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.padding.symmetric(horizontal=14, vertical=10))),
                ])),
            ft.Container(col={"xs":12,"sm":6,"lg":3}, content=_panel_dk(
                "Conseils IA", ft.Icons.PSYCHOLOGY_OUTLINED, PRIMARY, [
                    *(
                        [
                            ft.Container(
                                bgcolor="#0F2D5E", border=ft.border.all(1, "#2563EB"),
                                border_radius=8,
                                padding=ft.padding.symmetric(horizontal=10, vertical=7),
                                content=ft.Row(controls=[
                                    ft.Icon(ft.Icons.INFO_OUTLINED, color=PRIMARY, size=13),
                                    ft.Text(f"[{al['code_theme']}] {al['message']}",
                                            size=10, color=_DK_TEXT, expand=True, max_lines=2),
                                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            )
                            for al in alerts_data[:3]
                        ]
                        if alerts_data else [
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED, color=SUCCESS, size=14),
                                ft.Text("Banque de themes en bonne sante.", size=11, color=SUCCESS),
                            ], spacing=6)
                        ]
                    ),
                    ft.OutlinedButton("Suggestions IA", icon=ft.Icons.AUTO_AWESOME_OUTLINED,
                        on_click=suggest_ai_theme,
                        style=ft.ButtonStyle(color=PRIMARY, side=ft.BorderSide(1,PRIMARY),
                            shape=ft.RoundedRectangleBorder(radius=8))),
                ])),
        ], spacing=10, run_spacing=10)

        bank_area.controls = [
            stats_row,
            action_bar,
            filter_bar,
            form_panel,
            main_split,
            footer,
        ]

    # ── RENDER CAMPAGNES ──────────────────────────────────────────────────────
    def render_campaigns() -> None:
        is_editing = bool(state.get("editing_campaign_id"))
        campaigns: list[dict[str, Any]] = []
        try:
            campaigns = list_toolbox_campaigns()
        except Exception:
            pass

        total_campaigns = len(campaigns)
        max_page_c = max(0, (total_campaigns - 1) // PAGE_SIZE) if total_campaigns else 0
        state["page_campaigns"] = max(0, min(max_page_c, state["page_campaigns"]))
        start_c = state["page_campaigns"] * PAGE_SIZE
        page_campaigns = campaigns[start_c : start_c + PAGE_SIZE]

        active_count  = sum(1 for c in campaigns if c.get("status") == "active")
        planned_count = sum(1 for c in campaigns if c.get("status") == "planifiee")
        ended_count   = sum(1 for c in campaigns if c.get("status") == "terminee")

        stats_row_c = ft.ResponsiveRow(controls=[
            _kpi("Total campagnes", len(campaigns), PRIMARY, ft.Icons.CAMPAIGN_OUTLINED),
            _kpi("Actives",         active_count,   SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
            _kpi("Planifiees",      planned_count,  WARNING, ft.Icons.PENDING_OUTLINED),
            _kpi("Terminees",       ended_count,    MUTED,   ft.Icons.TASK_ALT_OUTLINED),
        ], spacing=12, run_spacing=12)

        form_panel_c = _panel(
            "Modifier la campagne" if is_editing else "Nouvelle campagne HSE",
            ft.Icons.EDIT_NOTE_OUTLINED if is_editing else ft.Icons.ADD_CIRCLE_OUTLINED,
            WARNING if is_editing else _TEAL, [
                ft.Text(
                    "Une campagne active (date debut <= aujourd'hui <= date fin) booste "
                    "les themes associes de +45 points dans le planificateur intelligent.",
                    size=12, color=MUTED),
                ft.Row(controls=[camp_name_field, camp_code_field], wrap=True, spacing=10),
                ft.Row(controls=[camp_desc_field], wrap=True),
                ft.Row(controls=[camp_category, camp_start_field, camp_end_field,
                                  camp_status_field, camp_site_field], wrap=True, spacing=10),
                ft.Row(controls=[
                    _primary_btn("Modifier" if is_editing else "Creer la campagne",
                                 ft.Icons.SAVE_OUTLINED, save_campaign),
                    ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE_OUTLINED, visible=is_editing,
                        style=ft.ButtonStyle(color=DANGER, side=ft.BorderSide(1,DANGER),
                                             shape=ft.RoundedRectangleBorder(radius=8)),
                        on_click=lambda e: (_reset_campaign_form(),
                                             notify("Edition annulee.", MUTED),
                                             render_campaigns(), _upd())),
                ], wrap=True, spacing=10),
            ],
        )

        if campaigns:
            camp_table = ft.Container(
                bgcolor=_W, border=ft.border.all(1,_TEAL_BD), border_radius=10, padding=0,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Code",      weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Nom",       weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Categorie", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Debut",     weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Fin",       weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Statut",    weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Site",      weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Themes",    weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Actions",   weight=ft.FontWeight.BOLD)),
                        ],
                        rows=[ft.DataRow(cells=[
                            ft.DataCell(_code_chip(str(r.get("code_campaign") or "-"))),
                            ft.DataCell(ft.Text(str(r.get("name") or "—"), width=200,
                                max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, weight=ft.FontWeight.W_500)),
                            ft.DataCell(_mini_badge(str(r.get("category") or "—"), _TEAL)),
                            ft.DataCell(ft.Text(str(r.get("start_date") or "—"), size=12, color=MUTED)),
                            ft.DataCell(ft.Text(str(r.get("end_date") or "—"), size=12, color=MUTED)),
                            ft.DataCell(_campaign_status_badge(str(r.get("status") or "planifiee"))),
                            ft.DataCell(ft.Text(str(r.get("site") or "Tous"), size=12, color=MUTED)),
                            ft.DataCell(ft.Container(bgcolor=_BSF, border_radius=10,
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                content=ft.Text(str(r.get("themes_count") or 0),
                                    size=12, color=PRIMARY, weight=ft.FontWeight.BOLD))),
                            ft.DataCell(ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, icon_size=18,
                                tooltip="Modifier", on_click=lambda e, row=r: edit_campaign(row))),
                        ]) for r in page_campaigns],
                        border=None, border_radius=0, heading_row_color=_TEAL_SF,
                    )
                ]),
            )
        else:
            camp_table = ft.Container(bgcolor=_TEAL_SF, border=ft.border.all(1,_TEAL_BD),
                border_radius=10, padding=20,
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, color=_TEAL, size=20),
                    ft.Text("Aucune campagne. Cree ta premiere campagne HSE pour booster la planification intelligente.",
                            color=MUTED, size=13),
                ], spacing=10))

        campaigns_area.controls = [
            stats_row_c,
            ft.ResponsiveRow(controls=[
                ft.Container(col={"xs":12,"lg":12}, content=form_panel_c),
            ], spacing=12, run_spacing=12),
            camp_table,
            pagination_row(
                current_page=state["page_campaigns"],
                max_page=max_page_c,
                total=total_campaigns,
                shown_start=start_c + 1 if page_campaigns else 0,
                shown_end=start_c + len(page_campaigns),
                item_label="campagne(s)",
                on_prev=lambda: (state.__setitem__("page_campaigns", state["page_campaigns"] - 1), render_campaigns(), _upd()),
                on_next=lambda: (state.__setitem__("page_campaigns", state["page_campaigns"] + 1), render_campaigns(), _upd()),
                on_page=lambda p: (state.__setitem__("page_campaigns", p), render_campaigns(), _upd()),
            ),
        ]

    # ── RENDER HISTORIQUE ─────────────────────────────────────────────────────
    def render_history() -> None:
        snap         = state.get("snapshot") or {}
        history_rows = snap.get("history") or []
        try:
            usage_rows = list_toolbox_theme_usage()
        except Exception:
            usage_rows = []
        try:
            eff_rows = list_toolbox_effectiveness()
        except Exception:
            eff_rows = []

        eval_opts = [
            ft.dropdown.Option(
                str(r["id_usage"]),
                f"{r.get('usage_date','-')} — {str(r.get('topic_en') or r.get('theme_fr') or '-')[:40]}")
            for r in usage_rows[:30]
        ]
        usage_select = ft.Dropdown(
            label="Session a evaluer", width=420, border_radius=8,
            fill_color="#0A1929", color="#E2E8F0", border_color="#1E3A5F",
            focused_border_color="#2563EB", label_style=ft.TextStyle(color="#9DB0C5"),
            text_style=ft.TextStyle(color="#E2E8F0"),
            options=eval_opts,
        )

        def _do_save_eff(e: ft.ControlEvent) -> None:
            uid = usage_select.value
            if not uid:
                notify("Selectionne une session.", DANGER); _upd(); return
            save_effectiveness(int(uid), e)

        eval_panel = _panel("Evaluation d'effectivite", ft.Icons.STAR_OUTLINED, _PRP, [
            ft.Text("Poids : participation 30% | comprehension 45% | facilitateur 15% | qualite 10%",
                    size=11, color=MUTED),
            ft.Row(controls=[usage_select], wrap=True, spacing=10),
            ft.Row(controls=[participation_field, comprehension_field,
                              facilitator_rating, session_quality_field], wrap=True, spacing=10),
            ft.Row(controls=[effectiveness_comments], wrap=True),
            ft.Row(controls=[_primary_btn("Enregistrer l'evaluation", ft.Icons.SAVE_OUTLINED, _do_save_eff)],
                   wrap=True, spacing=10),
        ])

        if eff_rows:
            eff_table = ft.Container(bgcolor=_W, border=ft.border.all(1,_BBD), border_radius=10, padding=0,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Date",          weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Theme",         weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Facilitateur",  weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Participants",  weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Participation", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Comprehension", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Score global",  weight=ft.FontWeight.BOLD)),
                        ],
                        rows=[ft.DataRow(cells=[
                            ft.DataCell(ft.Text(str(r.get("usage_date","-")), weight=ft.FontWeight.W_500)),
                            ft.DataCell(ft.Text(str(r.get("topic_en") or r.get("theme_fr") or "-"), width=200)),
                            ft.DataCell(ft.Text(str(r.get("facilitator") or "—"), color=MUTED, size=12)),
                            ft.DataCell(ft.Text(str(r.get("participants_count") or 0),
                                                color=PRIMARY, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(_score_bar(float(r.get("participation_rate") or 0))),
                            ft.DataCell(_score_bar(float(r.get("comprehension_score") or 0))),
                            ft.DataCell(_global_score_badge(float(r.get("global_score") or 0))),
                        ]) for r in eff_rows],
                        border=None, border_radius=0, heading_row_color=_PSF,
                    )
                ]))
            eff_section = _panel("Evaluations enregistrees", ft.Icons.QUERY_STATS_OUTLINED, _PRP, [eff_table])
        else:
            eff_section = ft.Container()

        hist_table = _panel("Historique des sessions", ft.Icons.HISTORY_OUTLINED, PRIMARY, [
            ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                professional_data_table(
                    columns=[
                        ft.DataColumn(ft.Text("Date",         weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Theme",        weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Facilitateur", weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Participants", weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Realisation",  weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Fiche",        weight=ft.FontWeight.BOLD)),
                    ],
                    rows=[ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(r.get("date_theme","-")), weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(str(r.get("theme","-")), width=300,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)),
                        ft.DataCell(ft.Text(str(r.get("facilitateur") or "—"), color=MUTED, size=12)),
                        ft.DataCell(ft.Container(
                            bgcolor=_GSF if int(r.get("attendees_count",0))>0 else _SLT,
                            border_radius=10, padding=ft.padding.symmetric(horizontal=7, vertical=3),
                            content=ft.Row(controls=[
                                ft.Icon(ft.Icons.GROUPS_OUTLINED, size=13,
                                    color=SUCCESS if int(r.get("attendees_count",0))>0 else MUTED),
                                ft.Text(str(r.get("attendees_count",0)), size=12,
                                    color=SUCCESS if int(r.get("attendees_count",0))>0 else MUTED,
                                    weight=ft.FontWeight.BOLD),
                            ], spacing=4, tight=True),
                        )),
                        ft.DataCell(_state_badge("done" if r.get("realized") else "missing")),
                        ft.DataCell(ft.IconButton(ft.Icons.PRINT_OUTLINED, icon_color=_TEAL, icon_size=18,
                            tooltip="Exporter fiche de presence",
                            on_click=lambda e, d=str(r.get("date_theme","")): export_attendance(d))),
                    ]) for r in history_rows],
                    border=None, border_radius=0, heading_row_color=_BHD,
                )
            ]),
        ])

        export_panel = _panel("Export mensuel", ft.Icons.DOWNLOAD_FOR_OFFLINE_OUTLINED, SUCCESS, [
            ft.Row(controls=[
                _primary_btn("Exporter rapport mensuel", ft.Icons.DOWNLOAD_OUTLINED, export_excel),
                ft.Text("Export XLSX bilingue avec zones de signature.", size=12, color=MUTED),
            ], wrap=True, spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ])

        history_area.controls = [eval_panel, eff_section, hist_table, export_panel]

    # ── RENDER PRINCIPAL ──────────────────────────────────────────────────────
    def render() -> None:
        data    = state.get("data") or {"summary":{}, "rows":[], "label":""}
        summary = data["summary"]
        summary_row.controls = [
            _kpi_dk_top("Mois",        data.get("label") or "—",    PRIMARY, ft.Icons.CALENDAR_MONTH_OUTLINED),
            _kpi_dk_top("Jours",       summary.get("days",0),        PRIMARY, ft.Icons.DATE_RANGE_OUTLINED),
            _kpi_dk_top("Renseignes",  summary.get("completed",0),   SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
            _kpi_dk_top("A completer", summary.get("missing",0),     DANGER,  ft.Icons.REPORT_PROBLEM_OUTLINED),
            _kpi_dk_top("Avancement",  f"{summary.get('completion',0)}%", WARNING, ft.Icons.INSIGHTS_OUTLINED),
        ]
        render_dashboard()
        render_planning()
        render_realization()
        render_bank()
        render_campaigns()
        render_history()

    status_filter.on_change = lambda e: (render(), _upd())
    for _bf in (bank_cat_filter, bank_risk_filter, bank_freq_filter, bank_stat_filter, bank_site_filter):
        _bf.on_change = lambda e: (render_bank(), _upd())
    bank_search_tf.on_change = lambda e: (render_bank(), _upd())
    bank_search_tf.on_submit = lambda e: (render_bank(), _upd())

    # ── navigation ────────────────────────────────────────────────────────────
    tab_buttons: dict[str, ft.TextButton] = {}
    sections:    dict[str, ft.Control]    = {}

    def switch_tab(tab: str) -> None:
        state["tab"] = tab
        for key, sec in sections.items():
            sec.visible = (key == tab)
        for key, btn in tab_buttons.items():
            active = key == tab
            btn.style = ft.ButtonStyle(
                bgcolor=PRIMARY if active else _DK_CARD,
                color=_W if active else _DK_MUTED,
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                shape=ft.RoundedRectangleBorder(radius=8),
                elevation=2 if active else 0,
                side=None if active else ft.BorderSide(1, _DK_BORDER),
            )
        _upd()

    for key, label, icon in [
        ("dashboard",   "Tableau de bord",          ft.Icons.DASHBOARD_OUTLINED),
        ("planning",    "Planning",                 ft.Icons.AUTO_AWESOME_OUTLINED),
        ("realization", "Realisation",              ft.Icons.FACT_CHECK_OUTLINED),
        ("bank",        "Banque des themes",        ft.Icons.ACCOUNT_BALANCE_OUTLINED),
        ("campaigns",   "Campagnes HSE",            ft.Icons.CAMPAIGN_OUTLINED),
        ("history",     "Historique & Effectivite", ft.Icons.QUERY_STATS_OUTLINED),
    ]:
        tab_buttons[key] = ft.TextButton(label, icon=icon,
            on_click=lambda e, k=key: switch_tab(k))

    sections["dashboard"]   = ft.Column([today_banner, dashboard_area],  spacing=14, visible=True)
    sections["planning"]    = ft.Column([planning_area],                  spacing=14, visible=False)
    sections["realization"] = ft.Column([realization_area],               spacing=10, visible=False)
    sections["bank"]        = ft.Column([bank_area],                      spacing=14, visible=False)
    sections["campaigns"]   = ft.Column([campaigns_area],                 spacing=14, visible=False)
    sections["history"]     = ft.Column([history_area],                   spacing=14, visible=False)

    tab_bar = ft.Container(
        bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        content=ft.Row(list(tab_buttons.values()), wrap=True, spacing=6),
    )
    control_bar = ft.Container(
        bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=12,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        content=ft.Row(controls=[
            ft.Row(controls=[month_field, status_filter], spacing=10,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row(controls=[
                _primary_btn("Charger le mois", ft.Icons.CALENDAR_MONTH_OUTLINED, refresh),
                _dk_outline_btn("Actualiser", ft.Icons.REFRESH_OUTLINED, refresh),
                _dk_outline_btn("Exporter Excel", ft.Icons.DOWNLOAD_OUTLINED, export_excel),
            ], spacing=8),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True, spacing=10,
           vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )

    root = ft.Column(
        controls=[
            module_header("Toolbox Talk",
                "Planification intelligente, campagnes HSE, realisation, effectivite et analyse."),
            control_bar, summary_row, tab_bar, *sections.values(),
        ],
        spacing=16, expand=True, scroll=ft.ScrollMode.AUTO,
    )
    switch_tab("bank")
    refresh()
    return ft.Container(bgcolor="#071321", expand=True, content=root)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSANTS UI
# ═══════════════════════════════════════════════════════════════════════════════

def _panel(title: str, icon: str, accent: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        bgcolor=_W, border=ft.border.all(1, _soft_bdr(accent)), border_radius=12, padding=0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(controls=[
            ft.Container(bgcolor=_soft_bg(accent), padding=ft.padding.symmetric(horizontal=16, vertical=10),
                content=ft.Row(controls=[
                    ft.Icon(icon, color=accent, size=18),
                    ft.Text(title, color=accent, size=14, weight=ft.FontWeight.BOLD),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)),
            ft.Container(padding=ft.padding.symmetric(horizontal=16, vertical=12),
                content=ft.Column(controls=controls, spacing=10)),
        ], spacing=0),
    )


def _kpi(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        col={"xs":12,"sm":6,"md":4,"lg":3,"xl":2},
        content=ft.Container(
            bgcolor=_W, border=ft.border.all(1,_soft_bdr(color)), border_radius=12, padding=0,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Row(controls=[
                ft.Container(width=4, bgcolor=color, expand=False),
                ft.Container(expand=True, padding=ft.padding.only(left=10,right=12,top=12,bottom=12),
                    content=ft.Column(controls=[
                        ft.Row(controls=[
                            ft.Container(width=34, height=34, bgcolor=_soft_bg(color), border_radius=8,
                                alignment=ft.Alignment(0,0),
                                content=ft.Icon(icon, color=color, size=17)),
                            ft.Text(str(label), color="#475569", size=10, weight=ft.FontWeight.W_500,
                                expand=True, max_lines=2),
                        ], spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Text(str(value), size=22, weight=ft.FontWeight.BOLD, color="#0F172A"),
                    ], spacing=4)),
            ], spacing=0),
        ),
    )


def _day_card(row: dict[str, Any]) -> ft.Control:
    done   = row.get("status") == "done"
    accent = SUCCESS if done else DANGER
    bg, bdr = (_GSF, _GBD) if done else (_RSF, _RBD)
    return ft.Container(col={"xs":6,"sm":4,"md":3,"lg":2},
        content=ft.Container(bgcolor=bg, border=ft.border.all(1,bdr), border_radius=10, padding=10, height=88,
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Text(f"{str(row.get('weekday',''))[:3]}", size=10, color=accent, weight=ft.FontWeight.BOLD),
                    ft.Text(f" {row.get('day','')}", size=12, color="#0F172A", weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.Icon(ft.Icons.CHECK_CIRCLE if done else ft.Icons.RADIO_BUTTON_UNCHECKED, color=accent, size=14),
                ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(_short(row.get("theme")), size=10,
                    color="#475569" if done else "#94A3B8",
                    max_lines=3, overflow=ft.TextOverflow.ELLIPSIS, italic=not done),
            ], spacing=4)))


def _tab_pill(label: str, key: str, current: str, on_click: Any) -> ft.Control:
    active = key == current
    return ft.TextButton(label, style=ft.ButtonStyle(
        bgcolor=PRIMARY if active else _TAB_OFF_BG, color=_W if active else _TAB_OFF_FG,
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        shape=ft.RoundedRectangleBorder(radius=16)), on_click=on_click)


def _primary_btn(label: str, icon: str, on_click: Any) -> ft.Control:
    return ft.ElevatedButton(label, icon=icon, on_click=on_click,
        style=ft.ButtonStyle(bgcolor=PRIMARY, color=_W, elevation=1,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14, vertical=10)))


def _outline_btn(label: str, icon: str, on_click: Any) -> ft.Control:
    return ft.OutlinedButton(label, icon=icon, on_click=on_click,
        style=ft.ButtonStyle(color=PRIMARY, side=ft.BorderSide(1,PRIMARY),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14, vertical=10)))


def _danger_btn(label: str, icon: str, on_click: Any) -> ft.Control:
    return ft.OutlinedButton(label, icon=icon, on_click=on_click,
        style=ft.ButtonStyle(color=DANGER, side=ft.BorderSide(1,DANGER),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14, vertical=10)))


def _icon_btn(icon: str, tooltip: str, on_click: Any, color: str) -> ft.Control:
    return ft.IconButton(icon=icon, icon_color=color, icon_size=20, tooltip=tooltip,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.padding.all(8)),
        on_click=on_click)


def _state_badge(state_val: str) -> ft.Control:
    done  = state_val == "done"
    color = SUCCESS if done else DANGER
    return ft.Container(bgcolor=_soft_bg(color), border=ft.border.all(1,_soft_bdr(color)),
        border_radius=20, padding=ft.padding.symmetric(horizontal=9, vertical=4),
        content=ft.Row(controls=[
            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE if done else ft.Icons.PENDING_OUTLINED, color=color, size=13),
            ft.Text("Renseigne" if done else "A completer", size=11, color=color, weight=ft.FontWeight.W_500),
        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER, tight=True))


def _mini_badge(label: str, color: str) -> ft.Control:
    return ft.Container(bgcolor=_soft_bg(color), border=ft.border.all(1,_soft_bdr(color)),
        border_radius=20, padding=ft.padding.symmetric(horizontal=8, vertical=3),
        content=ft.Text(label, size=10, color=color, weight=ft.FontWeight.W_500))


def _risk_badge(level: str) -> ft.Control:
    color = {"critique":DANGER, "eleve":WARNING, "moyen":PRIMARY, "faible":SUCCESS}.get(level, MUTED)
    return _mini_badge(level.title(), color)


def _campaign_status_badge(status: str) -> ft.Control:
    color = {"active":SUCCESS, "planifiee":WARNING, "terminee":MUTED, "annulee":DANGER}.get(status, MUTED)
    label = {"active":"Active", "planifiee":"Planifiee", "terminee":"Terminee", "annulee":"Annulee"}.get(status, status)
    return _mini_badge(label, color)


def _code_chip(code: str) -> ft.Control:
    return ft.Container(bgcolor=_BSF, border_radius=6, padding=ft.padding.symmetric(horizontal=7, vertical=3),
        content=ft.Text(code, size=11, weight=ft.FontWeight.BOLD, color=PRIMARY))


def _score_bar(score: float) -> ft.Control:
    pct   = max(0.0, min(score, 100.0))
    color = SUCCESS if pct >= 75 else WARNING if pct >= 50 else DANGER
    return ft.Column(controls=[
        ft.Text(f"{pct:.0f}%", size=11, color=color, weight=ft.FontWeight.BOLD),
        ft.ProgressBar(value=pct/100, color=color, bgcolor=_SBD, height=5, border_radius=3),
    ], spacing=2, width=80)


def _global_score_badge(score: float) -> ft.Control:
    color = SUCCESS if score >= 75 else WARNING if score >= 50 else DANGER
    return ft.Container(bgcolor=_soft_bg(color), border=ft.border.all(1,_soft_bdr(color)),
        border_radius=20, padding=ft.padding.symmetric(horizontal=10, vertical=4),
        content=ft.Text(f"{score:.1f}/100", size=12, color=color, weight=ft.FontWeight.BOLD))


def _progress_bar(label: str, value: Any, color: str) -> ft.Control:
    pct = max(0.0, min(float(value or 0), 100.0))
    return ft.Column(controls=[
        ft.Row(controls=[ft.Text(label, size=12, color="#475569", expand=True),
                         ft.Text(f"{pct:g}%", size=12, color=color, weight=ft.FontWeight.BOLD)]),
        ft.ProgressBar(value=pct/100, color=color, bgcolor=_SBD, height=6, border_radius=3),
    ], spacing=6)


def _metric_bar(label: str, value: int, total: int, color: str) -> ft.Control:
    pct = round(value*100/max(total,1))
    return ft.Row(controls=[
        ft.Text(label, color="#475569", size=12, expand=True),
        ft.Container(width=140, content=ft.ProgressBar(value=pct/100, color=color, bgcolor=_SBD, height=6, border_radius=3)),
        ft.Container(width=28, alignment=ft.Alignment(1,0),
            content=ft.Text(str(value), color=color, size=12, weight=ft.FontWeight.BOLD)),
    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def _session_row(date: str, theme: str, attendees: int, realized: bool) -> ft.Control:
    color = SUCCESS if realized else WARNING
    return ft.Container(border=ft.border.only(bottom=ft.BorderSide(1,"#F1F5F9")),
        padding=ft.padding.symmetric(vertical=8),
        content=ft.Row(controls=[
            ft.Container(width=30, height=30, border_radius=15, bgcolor=_soft_bg(color),
                alignment=ft.Alignment(0,0),
                content=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE if realized else ft.Icons.SCHEDULE_OUTLINED,
                    color=color, size=15)),
            ft.Text(date, size=11, color="#94A3B8", width=90),
            ft.Text(theme, size=12, color="#1E293B", expand=True,
                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Container(bgcolor=_soft_bg(color), border_radius=12,
                padding=ft.padding.symmetric(horizontal=7, vertical=2),
                content=ft.Text(f"{attendees} part.", size=11, color=color, weight=ft.FontWeight.W_500)),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER))


def _short(value: Any) -> str:
    text = str(value or "A completer")
    return text.split(" / ", 1)[0] if " / " in text else text


def _kpi_dk_top(label: str, value: Any, color: str, icon: str) -> ft.Control:
    """Dark KPI card WITHOUT expand=True — safe for use directly inside a scrollable Column."""
    _OV = {PRIMARY:"#0F2D5E", SUCCESS:"#052E16", DANGER:"#3B0F0F",
           WARNING:"#2D1600", _PRP:"#1E0A4E", _TEAL:"#042F2E"}
    return ft.Container(
        col={"xs":12,"sm":6,"md":4,"lg":3,"xl":2},
        content=ft.Container(
            bgcolor=_DK_CARD,
            border=ft.border.only(
                left=ft.BorderSide(4, color),
                top=ft.BorderSide(1, _DK_BORDER),
                right=ft.BorderSide(1, _DK_BORDER),
                bottom=ft.BorderSide(1, _DK_BORDER),
            ),
            border_radius=12,
            padding=ft.padding.only(left=14, right=14, top=12, bottom=12),
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Container(width=32, height=32,
                        bgcolor=_OV.get(color, "#0F2D5E"),
                        border_radius=8, alignment=ft.Alignment(0, 0),
                        content=ft.Icon(icon, color=color, size=16)),
                    ft.Text(str(label), color=_DK_MUTED, size=10,
                        weight=ft.FontWeight.W_500, expand=True, max_lines=2),
                ], spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(str(value), size=22, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
            ], spacing=4),
        ),
    )


def _soft_bg(color: str) -> str:
    return {SUCCESS:_GSF, DANGER:_RSF, WARNING:_ASF, PRIMARY:_BSF,
            _PRP:_PSF, MUTED:_SLT, "#64748B":_SLT, _TEAL:_TEAL_SF}.get(color, _BSF)


def _soft_bdr(color: str) -> str:
    return {SUCCESS:_GBD, DANGER:_RBD, WARNING:_ABD, PRIMARY:_BBD,
            _PRP:_PBD, MUTED:_SBD, "#64748B":_SBD, _TEAL:_TEAL_BD}.get(color, _BBD)


# ── Dark-cockpit helpers (Banque des themes) ──────────────────────────────────

def _dk_ov(color: str) -> str:
    return {PRIMARY:"#0F2D5E", SUCCESS:"#052E16", DANGER:"#3B0F0F",
            WARNING:"#2D1600", _PRP:"#1E0A4E", _TEAL:"#042F2E"}.get(color, "#111F35")


def _kpi_dk(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        col={"xs":12,"sm":6,"md":4,"lg":3,"xl":2},
        content=ft.Container(
            bgcolor=_DK_CARD,
            border=ft.border.only(
                left=ft.BorderSide(4, color),
                top=ft.BorderSide(1, _DK_BORDER),
                right=ft.BorderSide(1, _DK_BORDER),
                bottom=ft.BorderSide(1, _DK_BORDER),
            ),
            border_radius=12, padding=0, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Container(
                expand=True, padding=ft.padding.only(left=14, right=14, top=12, bottom=12),
                content=ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Container(width=32, height=32, bgcolor=_dk_ov(color),
                            border_radius=8, alignment=ft.Alignment(0, 0),
                            content=ft.Icon(icon, color=color, size=16)),
                        ft.Text(str(label), color=_DK_MUTED, size=10,
                            weight=ft.FontWeight.W_500, expand=True, max_lines=2),
                    ], spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(str(value), size=26, weight=ft.FontWeight.BOLD, color=_DK_TEXT),
                ], spacing=5),
            ),
        ),
    )


def _panel_dk(title: str, icon: str, accent: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER),
        border_radius=12, padding=0, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(controls=[
            ft.Container(
                bgcolor=_DK_HEAD,
                border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                content=ft.Row(controls=[
                    ft.Container(width=3, height=14, bgcolor=accent, border_radius=2),
                    ft.Icon(icon, color=accent, size=16),
                    ft.Text(title, color=_DK_TEXT, size=13, weight=ft.FontWeight.BOLD),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                content=ft.Column(controls=controls, spacing=10),
            ),
        ], spacing=0),
    )


def _dk_outline_btn(label: str, icon: str, on_click: Any) -> ft.Control:
    return ft.OutlinedButton(label, icon=icon, on_click=on_click,
        style=ft.ButtonStyle(color=_DK_TEXT, side=ft.BorderSide(1, _DK_BORDER),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=12, vertical=10)))


def _dk_stat_row(label: str, count: int, color: str) -> ft.Control:
    return ft.Row(controls=[
        ft.Container(width=8, height=8, bgcolor=color, border_radius=4),
        ft.Text(label, size=11, color=_DK_TEXT, expand=True),
        ft.Container(
            bgcolor=_dk_ov(color), border=ft.border.all(1, color),
            border_radius=12, padding=ft.padding.symmetric(horizontal=8, vertical=2),
            content=ft.Text(str(count), size=11, color=color, weight=ft.FontWeight.BOLD),
        ),
    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def _bank_table_dk(
    themes: list[dict[str, Any]],
    on_edit: Any,
    on_delete: Any,
) -> ft.Control:
    if not themes:
        return ft.Container(
            bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER), border_radius=12,
            padding=20,
            content=ft.Row(controls=[
                ft.Icon(ft.Icons.INFO_OUTLINE, color=PRIMARY, size=20),
                ft.Text(
                    "Aucun theme. Utilise 'Generer themes OREZONE' ou les filtres.",
                    color=_DK_MUTED, size=13,
                ),
            ], spacing=10),
        )

    risk_color = {"critique":DANGER, "eleve":WARNING, "moyen":PRIMARY, "faible":SUCCESS}
    status_color = {"actif":SUCCESS, "en_attente":WARNING, "inactif":MUTED, "obsolete":DANGER}

    def _badge(text: str, color: str) -> ft.Control:
        return ft.Container(
            bgcolor=_dk_ov(color), border=ft.border.all(1, color),
            border_radius=20, padding=ft.padding.symmetric(horizontal=8, vertical=3),
            content=ft.Text(text, size=10, color=color, weight=ft.FontWeight.W_600))

    rows: list[ft.DataRow] = []
    for r in themes:
        code   = str(r.get("code_theme") or f"TBX-{int(r['id_topic']):03d}")
        cat    = str(r.get("category") or "—")
        risk   = str(r.get("risk_level") or "moyen")
        fr     = str(r.get("theme_fr") or "—")
        en     = str(r.get("topic_en") or "—")
        freq   = str(r.get("frequency") or "—")
        last   = str(r.get("last_used_at") or "—")[:10]
        uses   = str(r.get("usage_count") or 0)
        score  = float(r.get("average_effectiveness") or 0)
        stat   = str(r.get("status") or "actif")
        rclr   = risk_color.get(risk, PRIMARY)
        sclr   = status_color.get(stat, MUTED)

        rows.append(ft.DataRow(cells=[
            ft.DataCell(ft.Container(
                bgcolor="#0F2D5E", border_radius=6,
                padding=ft.padding.symmetric(horizontal=7, vertical=3),
                content=ft.Text(code, size=11, weight=ft.FontWeight.BOLD, color=PRIMARY))),
            ft.DataCell(_badge(cat, PRIMARY)),
            ft.DataCell(_badge(risk.title(), rclr)),
            ft.DataCell(ft.Text(fr, size=11, color=_DK_TEXT, width=180, max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS)),
            ft.DataCell(ft.Text(en, size=11, color=_DK_MUTED, width=160, max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS)),
            ft.DataCell(ft.Text(freq.title(), size=11, color=_DK_MUTED)),
            ft.DataCell(ft.Text(last, size=11, color=_DK_MUTED)),
            ft.DataCell(ft.Text(uses, size=12, color=PRIMARY, weight=ft.FontWeight.BOLD)),
            ft.DataCell(ft.Column(controls=[
                ft.Text(f"{score:.0f}%", size=11, color=SUCCESS if score>=75 else WARNING if score>=50 else DANGER,
                        weight=ft.FontWeight.BOLD),
                ft.ProgressBar(value=score/100, color=SUCCESS if score>=75 else WARNING if score>=50 else DANGER,
                               bgcolor=_DK_TRACK, height=5, border_radius=3),
            ], spacing=2, width=80)),
            ft.DataCell(_badge(stat.replace("_"," ").title(), sclr)),
            ft.DataCell(ft.Row(controls=[
                ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=PRIMARY, icon_size=17,
                    tooltip="Modifier", on_click=lambda e, row=r: on_edit(row)),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, icon_size=17,
                    tooltip="Supprimer", on_click=lambda e, row=r: on_delete(row)),
            ], spacing=0)),
        ]))

    return ft.Container(
        bgcolor=_DK_CARD, border=ft.border.all(1, _DK_BORDER),
        border_radius=12, padding=0, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(controls=[
            ft.Container(
                bgcolor=_DK_HEAD,
                border=ft.border.only(bottom=ft.BorderSide(1, _DK_BORDER)),
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.TABLE_ROWS_OUTLINED, color=PRIMARY, size=16),
                    ft.Text("Banque des themes", color=_DK_TEXT, size=13, weight=ft.FontWeight.BOLD,
                            expand=True),
                    ft.Text(f"{len(themes)} theme(s)", size=12, color=_DK_MUTED),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ),
            ft.Container(
                bgcolor=_DK_CARD,
                content=ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Code",          color=_DK_MUTED, size=11, weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Categorie",     color=_DK_MUTED, size=11, weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Niveau risque", color=_DK_MUTED, size=11, weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Theme FR",      color=_DK_MUTED, size=11, weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Topic EN",      color=_DK_MUTED, size=11, weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Frequence",     color=_DK_MUTED, size=11, weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Derniere util.", color=_DK_MUTED, size=11, weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Utilisations",  color=_DK_MUTED, size=11, weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Score moy.",    color=_DK_MUTED, size=11, weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Statut",        color=_DK_MUTED, size=11, weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Actions",       color=_DK_MUTED, size=11, weight=ft.FontWeight.BOLD)),
                        ],
                        rows=rows,
                        bgcolor=_DK_CARD,
                        border=None,
                        border_radius=0,
                        horizontal_lines=ft.BorderSide(1, _DK_BORDER),
                        vertical_lines=ft.BorderSide(0, "transparent"),
                        heading_row_color=_DK_HEAD,
                        heading_row_height=44,
                        data_row_min_height=48,
                        data_row_max_height=80,
                        column_spacing=18,
                        horizontal_margin=14,
                        divider_thickness=0,
                        show_bottom_border=True,
                        show_checkbox_column=False,
                        heading_text_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=_DK_MUTED),
                        data_text_style=ft.TextStyle(size=11, color=_DK_TEXT),
                        data_row_color={
                            ft.ControlState.DEFAULT:  _DK_CARD,
                            ft.ControlState.HOVERED:  _DK_CARD2,
                            ft.ControlState.PRESSED:  "#0F2D5E",
                            ft.ControlState.SELECTED: "#0F2D5E",
                        },
                    )
                ]),
            ),
        ], spacing=0),
    )
