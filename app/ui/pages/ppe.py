from __future__ import annotations

import getpass
import socket
from typing import Any

import flet as ft

from app.services.lock_service import acquire_lock, get_lock_info, release_lock

from app.ui.components.tables import professional_data_table

from app.services import (
    assign_multiple_ppe,
    assign_required_ppe,
    close_all_employee_assignments,
    create_ppe_item,
    delete_ppe_item,
    delete_ppe_requirement,
    export_ppe_equipped_employees_xlsx,
    export_ppe_compliance_xlsx,
    export_ppe_inspections_xlsx,
    export_ppe_inventory_xls,
    get_ppe_options,
    get_employee_ppe_profile,
    get_employee_dotation_history,
    get_employees_with_metadata,
    get_expiring_assigned_ppe,
    get_ppe_summary,
    get_employees_dotation_list,
    get_sites_list,
    list_ppe_assignments,
    list_ppe_compliance,
    list_ppe_employee_compliance_summary,
    list_ppe_inspections,
    list_ppe_items,
    list_ppe_requirements,
    list_stock_movements,
    record_ppe_inspection,
    refresh_ppe_alerts,
    record_stock_movement,
    return_ppe_assignment,
    save_ppe_requirement,
    update_ppe_item,
    today_iso,
    export_ppe_dotation_sheet_pdf,
    open_dotation_file,
)
from app.ui.components.confirm import confirm_action
from app.ui.theme import DANGER, MUTED, PRIMARY, SUCCESS, TEXT, WARNING


from app.ui.components.dark_styles import BG, CARD, DARK_BORDER, DARK_MUTED, DARK_TEXT, FIELD
from app.ui.components.pagination import PAGE_SIZE, pagination_row


def ppe_page(page: ft.Page | None = None) -> ft.Control:
    status = ft.Text("", size=12, color=MUTED)
    selected_item_id: int | None = None

    # ── Shared content areas ───────────────────────────────────────────────────
    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    catalog_area = ft.Column(spacing=10)
    movement_area = ft.Column(spacing=10)
    assignment_area = ft.Column(spacing=10)
    requirement_area = ft.Column(spacing=8)
    compliance_area = ft.Column(spacing=8)
    inspection_area = ft.Column(spacing=8)
    alert_area = ft.Column(spacing=8)
    employee_profile_area = ft.Column(spacing=6)
    required_ppe_area = ft.Column(spacing=6)
    compliance_summary_area = ft.Column(spacing=6)
    assignment_basket_area = ft.Column(spacing=6)
    assignment_basket: list[dict[str, Any]] = []
    renewal_area = ft.Column(spacing=6, tight=True)
    history_area = ft.Column(spacing=6, tight=True)
    dotation_list_area = ft.Column(spacing=8)

    # ── 3-tab state ────────────────────────────────────────────────────────────
    state: dict[str, Any] = {
        "tab": "overview",
        "gestion_tab": "catalog",
        "selected_emp": None,
        "page": 0,
    }

    tab1_col = ft.Column(spacing=12)
    tab2_col = ft.Column(spacing=12)
    tab3_col = ft.Column(spacing=12)

    tab_buttons: dict[str, ft.TextButton] = {}

    # ── Multi-employee dotation state ──────────────────────────────────────────
    selected_employees: dict[int, dict[str, Any]] = {}
    employee_checkboxes: dict[int, ft.Checkbox] = {}
    employee_options_cache: list[dict[str, Any]] = []
    employees_meta_cache: list[dict[str, Any]] = []
    selected_count_text = ft.Text("0 employé(s) sélectionné(s)", color=DARK_MUTED, size=11, weight=ft.FontWeight.W_500)
    employee_list_area = ft.Column(spacing=4)

    # ── Form fields ────────────────────────────────────────────────────────────
    group_func_dd = ft.Dropdown(label="Par fonction", hint_text="Choisir...", width=220)
    group_site_dd = ft.Dropdown(label="Par site", hint_text="Choisir...", width=200)
    history_employee_dd = ft.Dropdown(label="Employé", width=320)
    emp_search_field = ft.TextField(label="Rechercher un employé", prefix_icon=ft.Icons.SEARCH, width=260)
    issued_by_field = ft.TextField(label="Remis par", hint_text="Responsable / Magasinier", width=220)
    search_field = ft.TextField(label="Recherche EPI", prefix_icon=ft.Icons.SEARCH, width=260)

    type_field = ft.Dropdown(label="Type EPI *", width=220)
    item_name_field = ft.TextField(label="Designation EPI *", hint_text="Ex: Casque de securite", width=260)
    size_field = ft.TextField(label="Taille / pointure", hint_text="Optionnel", width=160)
    standard_field = ft.TextField(label="Norme applicable", hint_text="Ex: EN 397", width=180)
    brand_field = ft.TextField(label="Marque", hint_text="Optionnel", width=160)
    model_field = ft.TextField(label="Modele / reference", hint_text="Optionnel", width=180)
    condition_field = ft.Dropdown(
        label="Etat", value="neuf", width=140,
        options=[
            ft.dropdown.Option("neuf", "Neuf"),
            ft.dropdown.Option("bon", "Bon"),
            ft.dropdown.Option("usage", "Usage"),
            ft.dropdown.Option("endommage", "Endommage"),
        ],
    )
    expiry_field = ft.TextField(label="Date expiration", hint_text="AAAA-MM-JJ - optionnel", width=190)
    initial_quantity_field = ft.TextField(label="Quantite recue", value="0", width=150)
    threshold_field = ft.TextField(label="Alerte stock a", value="0", width=150)
    save_item_button = ft.ElevatedButton("Enregistrer l'EPI", icon=ft.Icons.SAVE_OUTLINED)
    cancel_edit_button = ft.OutlinedButton("Annuler", icon=ft.Icons.CLOSE_OUTLINED, visible=False)

    movement_item_field = ft.Dropdown(label="EPI", width=300)
    movement_type_field = ft.Dropdown(
        label="Mouvement", value="entree", width=150,
        options=[
            ft.dropdown.Option("entree", "Entree"),
            ft.dropdown.Option("sortie", "Sortie"),
            ft.dropdown.Option("ajustement", "Ajustement"),
        ],
    )
    movement_quantity_field = ft.TextField(label="Quantite", value="1", width=120)
    movement_motif_field = ft.TextField(label="Motif", width=220)
    movement_reference_field = ft.TextField(label="Reference", width=160)
    movement_filter_item = ft.Dropdown(label="Filtrer par EPI", width=240)
    movement_filter_type = ft.Dropdown(
        label="Filtrer par mouvement", width=190,
        options=[
            ft.dropdown.Option("", "Tous les mouvements"),
            ft.dropdown.Option("entree", "Entree"),
            ft.dropdown.Option("sortie", "Sortie"),
            ft.dropdown.Option("ajustement", "Ajustement"),
        ],
    )
    movement_filter_employee = ft.TextField(label="Filtrer par employe", prefix_icon=ft.Icons.SEARCH, width=230)
    movement_filter_date = ft.TextField(label="Filtrer par date", hint_text="AAAA-MM-JJ", width=180)

    assignment_employee_field = ft.Dropdown(label="Employe", width=320)
    assignment_item_field = ft.Dropdown(label="EPI", width=300)
    assignment_quantity_field = ft.TextField(label="Quantite", value="1", width=120)
    assignment_date_field = ft.TextField(label="Date remise", value=today_iso(), width=160)
    assignment_observation_field = ft.TextField(label="Observation", width=260)

    requirement_function_field = ft.Dropdown(label="Fonction", width=260)
    requirement_type_field = ft.Dropdown(label="Type EPI requis", width=240)
    requirement_quantity_field = ft.TextField(label="Quantite", value="1", width=120)
    requirement_mandatory_field = ft.Checkbox(label="Obligatoire", value=True)

    inspection_item_field = ft.Dropdown(label="EPI inspecte", width=300)
    inspection_status_field = ft.Dropdown(
        label="Statut inspection", value="ok", width=170,
        options=[
            ft.dropdown.Option("ok", "OK"),
            ft.dropdown.Option("a_surveiller", "A surveiller"),
            ft.dropdown.Option("endommage", "Endommage"),
            ft.dropdown.Option("hors_service", "Hors service"),
        ],
    )
    inspection_date_field = ft.TextField(label="Date inspection", value=today_iso(), width=160)
    inspection_next_field = ft.TextField(label="Prochaine inspection", hint_text="AAAA-MM-JJ", width=180)
    inspection_inspector_field = ft.TextField(label="Inspecteur", width=160)
    inspection_observation_field = ft.TextField(label="Observation", width=260)

    for _ctrl in (
        emp_search_field, issued_by_field, group_func_dd, group_site_dd, history_employee_dd,
        search_field, type_field, item_name_field, size_field, standard_field, brand_field,
        model_field, condition_field, expiry_field, initial_quantity_field, threshold_field,
        movement_item_field, movement_type_field, movement_quantity_field, movement_motif_field,
        movement_reference_field, movement_filter_item, movement_filter_type,
        movement_filter_employee, movement_filter_date, assignment_employee_field,
        assignment_item_field, assignment_quantity_field, assignment_date_field,
        assignment_observation_field, requirement_function_field, requirement_type_field,
        requirement_quantity_field, inspection_item_field, inspection_status_field,
        inspection_date_field, inspection_next_field, inspection_inspector_field,
        inspection_observation_field,
    ):
        _ctrl.bgcolor = FIELD
        _ctrl.color = DARK_TEXT
        _ctrl.border_color = DARK_BORDER
        _ctrl.focused_border_color = PRIMARY
        _ctrl.label_style = ft.TextStyle(color=DARK_MUTED)

    # ── Utilities ──────────────────────────────────────────────────────────────

    def notify(message: str, color: str = MUTED) -> None:
        status.value = message
        status.color = color

    def _update() -> None:
        try:
            root.update()
        except RuntimeError:
            pass

    def refresh(event: ft.ControlEvent | None = None) -> None:
        try:
            refresh_options()
            render_summary()
            render_catalog()
            render_movements()
            render_assignments()
            render_requirements()
            render_inspections()
            render_alerts()
            render_compliance_summary()
            render_dotation_list()
            render_renewal_panel()
            render_active_tab()
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def refresh_options() -> None:
        options = get_ppe_options()
        type_field.options = [ft.dropdown.Option(str(r["value"]), str(r["label"])) for r in options["types"]]
        item_options = [ft.dropdown.Option(str(r["value"]), str(r["label"])) for r in options["items"]]
        movement_item_field.options = item_options
        movement_filter_item.options = [ft.dropdown.Option("", "Tous les EPI"), *item_options]
        assignment_item_field.options = item_options
        inspection_item_field.options = item_options
        requirement_type_field.options = [ft.dropdown.Option(str(r["value"]), str(r["label"])) for r in options["types"]]
        requirement_function_field.options = [ft.dropdown.Option(str(r["value"]), str(r["label"])) for r in options["functions"]]
        assignment_employee_field.options = [ft.dropdown.Option(str(r["value"]), str(r["label"])) for r in options["employees"]]
        if type_field.options and not type_field.value:
            type_field.value = type_field.options[0].key
        if requirement_type_field.options and not requirement_type_field.value:
            requirement_type_field.value = requirement_type_field.options[0].key
        if requirement_function_field.options and not requirement_function_field.value:
            requirement_function_field.value = requirement_function_field.options[0].key
        if item_options:
            movement_item_field.value = movement_item_field.value or item_options[0].key
            assignment_item_field.value = assignment_item_field.value or item_options[0].key
            inspection_item_field.value = inspection_item_field.value or item_options[0].key
        if assignment_employee_field.options and not assignment_employee_field.value:
            assignment_employee_field.value = assignment_employee_field.options[0].key
        employee_options_cache.clear()
        employee_options_cache.extend(options["employees"])
        try:
            employees_meta_cache.clear()
            employees_meta_cache.extend(get_employees_with_metadata())
        except Exception:
            pass
        group_func_dd.options = [ft.dropdown.Option("", "Toutes fonctions"), *[
            ft.dropdown.Option(str(r["value"]), str(r["label"])) for r in options["functions"]
        ]]
        try:
            site_opts = get_sites_list()
        except Exception:
            site_opts = []
        group_site_dd.options = [ft.dropdown.Option("", "Tous sites"), *[
            ft.dropdown.Option(str(r["value"]), str(r["label"])) for r in site_opts
        ]]
        history_employee_dd.options = [ft.dropdown.Option(str(r["value"]), str(r["label"])) for r in options["employees"]]
        render_employee_list()

    # ── EPI item CRUD ──────────────────────────────────────────────────────────

    def prepare_employee_assignment(event: ft.ControlEvent | None = None) -> None:
        try:
            profile = get_employee_ppe_profile(assignment_employee_field.value)
            employee_profile_area.controls = [
                _info_line("Fonction", profile.get("fonction") or "-", PRIMARY),
                _info_line("Site", profile.get("site") or "-", SUCCESS),
                _info_line("Badge", profile.get("numero_badge") or "Sans badge", WARNING),
            ]
            required_ppe_area.controls = [
                _required_ppe_row(r) for r in profile["requirements"]
            ] or [ft.Text("Aucun EPI obligatoire configure pour cette fonction.", color=DARK_MUTED, size=10)]
            notify("Dotation obligatoire comparee avec les EPI deja attribues.", SUCCESS)
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    assignment_employee_field.on_select = prepare_employee_assignment

    def assign_all_required(event: ft.ControlEvent | None = None) -> None:
        try:
            ids = assign_required_ppe(
                assignment_employee_field.value,
                assignment_date_field.value,
                assignment_observation_field.value,
            )
            notify(f"Dotation obligatoire attribuee: {len(ids)} EPI.", SUCCESS)
            refresh_ppe_alerts()
            refresh()
            prepare_employee_assignment()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def reset_item_form() -> None:
        nonlocal selected_item_id
        if selected_item_id is not None:
            release_lock("epi", str(selected_item_id), getpass.getuser())
        selected_item_id = None
        item_name_field.value = ""
        size_field.value = ""
        standard_field.value = ""
        brand_field.value = ""
        model_field.value = ""
        expiry_field.value = ""
        initial_quantity_field.value = "0"
        initial_quantity_field.disabled = False
        threshold_field.value = "0"
        save_item_button.text = "Enregistrer l'EPI"
        save_item_button.icon = ft.Icons.SAVE_OUTLINED
        cancel_edit_button.visible = False

    def save_item(event: ft.ControlEvent | None = None) -> None:
        try:
            payload = {
                "type_epi_id": type_field.value,
                "nom": item_name_field.value,
                "taille": size_field.value,
                "norme": standard_field.value,
                "marque": brand_field.value,
                "modele": model_field.value,
                "etat": condition_field.value,
                "date_expiration": expiry_field.value,
                "quantite_initiale": initial_quantity_field.value,
                "seuil_minimum": threshold_field.value,
            }
            if selected_item_id is None:
                create_ppe_item(payload)
                notify("EPI cree avec stock initialise.", SUCCESS)
            else:
                update_ppe_item(selected_item_id, payload)
                notify("EPI modifie.", SUCCESS)
            reset_item_form()
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def edit_item(row: dict[str, Any]) -> None:
        nonlocal selected_item_id
        item_id = int(row["id_epi"])
        current_user = getpass.getuser()
        if not acquire_lock("epi", str(item_id), current_user, socket.gethostname()):
            lock_info = get_lock_info("epi", str(item_id))
            if lock_info:
                msg = (
                    f"Fiche en cours de modification par {lock_info['utilisateur']}"
                    f" depuis {lock_info['verrouille_depuis']}"
                )
            else:
                msg = "Fiche verrouilee par un autre utilisateur."
            if page is not None:
                page.show_snack_bar(ft.SnackBar(ft.Text(msg), bgcolor=DANGER))
                page.update()
            else:
                notify(msg, DANGER)
                _update()
            return
        selected_item_id = item_id
        type_field.value = str(row["type_epi_id"])
        item_name_field.value = str(row.get("nom") or "")
        size_field.value = str(row.get("taille") or "")
        standard_field.value = str(row.get("norme") or "")
        brand_field.value = str(row.get("marque") or "")
        model_field.value = str(row.get("modele") or "")
        condition_field.value = str(row.get("etat") or "neuf")
        expiry_field.value = str(row.get("date_expiration") or "")
        initial_quantity_field.value = str(row.get("quantite_disponible") or 0)
        initial_quantity_field.disabled = True
        threshold_field.value = str(row.get("seuil_minimum") or 0)
        save_item_button.text = "Enregistrer"
        save_item_button.icon = ft.Icons.SAVE_OUTLINED
        cancel_edit_button.visible = True
        notify("Mode modification active.", PRIMARY)
        state["gestion_tab"] = "catalog"
        switch_tab("gestion")

    def delete_item(item_id: int) -> None:
        confirm_action(
            page,
            "Supprimer ou desactiver l'EPI",
            "Le systeme supprimera l'EPI si possible, sinon il sera desactive pour conserver l'historique.",
            lambda: _delete_item(item_id),
            confirm_label="Continuer",
            danger=True,
        )

    def _delete_item(item_id: int) -> None:
        try:
            result = delete_ppe_item(item_id)
            reset_item_form()
            notify("EPI supprime." if result == "supprime" else "EPI desactive (historique conserve).", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def save_movement(event: ft.ControlEvent | None = None) -> None:
        try:
            record_stock_movement({
                "epi_id": movement_item_field.value,
                "type_mouvement": movement_type_field.value,
                "quantite": movement_quantity_field.value,
                "motif": movement_motif_field.value,
                "reference": movement_reference_field.value,
            })
            notify("Mouvement de stock enregistre.", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def add_assignment_to_basket(event: ft.ControlEvent | None = None) -> None:
        try:
            epi_id = int(str(assignment_item_field.value or "0"))
            quantity = int(str(assignment_quantity_field.value or "0"))
            if quantity <= 0:
                raise ValueError("La quantite doit etre superieure a zero.")
            label = next(
                (str(r["label"]) for r in get_ppe_options()["items"] if int(r["value"]) == epi_id),
                f"EPI {epi_id}",
            )
            existing = next((item for item in assignment_basket if int(item["epi_id"]) == epi_id), None)
            if existing:
                existing["quantite"] = int(existing["quantite"]) + quantity
            else:
                assignment_basket.append({
                    "epi_id": epi_id, "quantite": quantity, "label": label,
                    "date_remise": str(assignment_date_field.value or today_iso()),
                })
            render_assignment_basket()
            notify(f"{label} ajoute au panier.", PRIMARY)
        except Exception as exc:
            notify(str(exc), DANGER)
        _update()

    def remove_assignment_from_basket(epi_id: int) -> None:
        assignment_basket[:] = [item for item in assignment_basket if int(item["epi_id"]) != epi_id]
        render_assignment_basket()
        _update()

    def render_assignment_basket() -> None:
        if not assignment_basket:
            assignment_basket_area.controls = [
                ft.Text("Ajoutez des EPI au panier avant de confirmer.", color=DARK_MUTED, size=10)
            ]
            return

        def _date_field(item: dict) -> ft.TextField:
            tf = ft.TextField(
                value=str(item.get("date_remise") or today_iso()),
                label="Date remise",
                hint_text="AAAA-MM-JJ",
                width=140,
                bgcolor=FIELD,
                color=DARK_TEXT,
                border_color=DARK_BORDER,
                focused_border_color=PRIMARY,
                label_style=ft.TextStyle(color=DARK_MUTED),
                text_size=11,
                on_change=lambda e, it=item: it.update({"date_remise": e.control.value}),
            )
            return tf

        assignment_basket_area.controls = [
            ft.Text("Panier de dotation", color=DARK_TEXT, size=12, weight=ft.FontWeight.BOLD),
            *[
                ft.Container(
                    bgcolor=FIELD, border=ft.border.all(1, DARK_BORDER), border_radius=8,
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    content=ft.Row([
                        ft.Icon(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, color="#60A5FA", size=16),
                        ft.Text(str(item["label"]), color=DARK_TEXT, size=10, expand=True),
                        ft.Container(
                            bgcolor=PRIMARY + "22",
                            border=ft.border.all(1, PRIMARY),
                            border_radius=10,
                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            content=ft.Text(f"×{item['quantite']}", color=PRIMARY, size=10, weight=ft.FontWeight.BOLD),
                        ),
                        _date_field(item),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE, tooltip="Retirer du panier", icon_color=DANGER,
                            on_click=lambda e, eid=int(item["epi_id"]): remove_assignment_from_basket(eid),
                        ),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
                for item in assignment_basket
            ],
        ]

    # ── Retour en masse ────────────────────────────────────────────────────────

    def _close_all_for_employee(emp_id: int, emp_name: str) -> None:
        confirm_action(
            page,
            "Retour total EPI",
            f"Tous les EPI actifs de {emp_name} seront clôturés et retournés au stock.",
            lambda: _do_close_all(emp_id),
            confirm_label="Confirmer le retour",
            danger=True,
        )

    def _do_close_all(emp_id: int) -> None:
        try:
            count = close_all_employee_assignments(emp_id)
            notify(f"{count} EPI retourné(s) au stock.", SUCCESS)
            refresh_ppe_alerts()
            render_dotation_list()
            _update()
        except Exception as exc:
            notify(f"Erreur : {exc}", DANGER)
            _update()

    # ── Dotation par groupe ────────────────────────────────────────────────────

    def _select_employees_by_group(e: Any = None) -> None:
        func_id = str(group_func_dd.value or "")
        site_id = str(group_site_dd.value or "")
        if not func_id and not site_id:
            notify("Sélectionnez une fonction ou un site.", WARNING)
            _update()
            return
        count = 0
        for emp in employees_meta_cache:
            match_func = not func_id or str(emp.get("fonction_id") or "") == func_id
            match_site = not site_id or str(emp.get("site_id") or "") == site_id
            if match_func and match_site:
                eid = int(emp["id_employe"])
                selected_employees[eid] = {
                    "id_employe": eid,
                    "nom": str(emp.get("nom") or ""),
                    "prenom": str(emp.get("prenom") or ""),
                    "matricule": str(emp.get("matricule") or ""),
                    "badge": str(emp.get("badge") or ""),
                    "fonction": str(emp.get("fonction") or ""),
                    "site": str(emp.get("site") or ""),
                }
                count += 1
        render_employee_list()
        _update_selected_count()
        notify(f"{count} employé(s) sélectionné(s).", SUCCESS)
        _update()

    # ── Historique par employé ─────────────────────────────────────────────────

    def render_employee_history(e: Any = None) -> None:
        emp_id = history_employee_dd.value
        if not emp_id:
            history_area.controls = [ft.Text("Sélectionnez un employé.", color=DARK_MUTED, italic=True, size=11)]
            try:
                history_area.update()
            except RuntimeError:
                pass
            return
        try:
            rows = get_employee_dotation_history(int(emp_id))
        except Exception as exc:
            history_area.controls = [ft.Text(f"Erreur : {exc}", color=DANGER, size=11)]
            try:
                history_area.update()
            except RuntimeError:
                pass
            return
        if not rows:
            history_area.controls = [ft.Text("Aucun historique.", color=DARK_MUTED, italic=True, size=11)]
            try:
                history_area.update()
            except RuntimeError:
                pass
            return
        _S = {"en_service": SUCCESS, "retourne": DARK_MUTED, "perdu": DANGER, "deteriore": WARNING, "vole": DANGER}
        cs = ft.TextStyle(color=PRIMARY, size=11, weight=ft.FontWeight.BOLD)
        hist_rows = []
        for row in rows:
            st = str(row.get("statut") or "en_service")
            clr = _S.get(st, DARK_MUTED)
            hist_rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(row.get("date_remise") or "—"), color=DARK_MUTED, size=10)),
                ft.DataCell(ft.Text(str(row.get("type_epi") or "—"), color=DARK_TEXT, size=10)),
                ft.DataCell(ft.Text(str(row.get("epi_nom") or "—"), color=DARK_TEXT, size=10, weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(f"×{row.get('quantite', 1)}", color=PRIMARY, size=10)),
                ft.DataCell(ft.Text(str(row.get("date_retour") or "—"), color=DARK_MUTED, size=10)),
                ft.DataCell(_status_badge(st.replace("_", " ").title(), clr)),
                ft.DataCell(ft.Text(str(row.get("observations") or "—"), color=DARK_MUTED, size=9, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)),
            ]))
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Date remise", style=cs)),
                ft.DataColumn(ft.Text("Type EPI", style=cs)),
                ft.DataColumn(ft.Text("Désignation", style=cs)),
                ft.DataColumn(ft.Text("Qté", style=cs)),
                ft.DataColumn(ft.Text("Date retour", style=cs)),
                ft.DataColumn(ft.Text("Statut", style=cs)),
                ft.DataColumn(ft.Text("Observation", style=cs)),
            ],
            rows=hist_rows,
            heading_row_color={ft.ControlState.DEFAULT: "#142B45"},
            data_row_color={ft.ControlState.DEFAULT: CARD},
            border=ft.border.all(1, DARK_BORDER),
            border_radius=8,
            column_spacing=12,
            data_row_min_height=44,
        )
        history_area.controls = [
            ft.Text(f"{len(rows)} mouvement(s) enregistré(s)", color=DARK_MUTED, size=11),
            ft.Container(bgcolor=CARD, border_radius=8, content=ft.Row(controls=[table], scroll=ft.ScrollMode.AUTO, tight=True)),
        ]
        try:
            history_area.update()
        except RuntimeError:
            pass

    history_employee_dd.on_change = render_employee_history

    # ── Renouvellement automatique ─────────────────────────────────────────────

    def render_renewal_panel(e: Any = None) -> None:
        try:
            rows = get_expiring_assigned_ppe(30)
        except Exception:
            rows = []
        if not rows:
            renewal_area.controls = [
                ft.Text("Aucun EPI expirant dans les 30 prochains jours.", color=SUCCESS, size=11, italic=True)
            ]
            try:
                renewal_area.update()
            except RuntimeError:
                pass
            return
        cards: list[ft.Control] = []
        for row in rows:
            jours = int(row.get("jours_restants") or 0)
            clr = DANGER if jours <= 7 else WARNING if jours <= 15 else PRIMARY
            emp_name = f"{row.get('nom', '')} {row.get('prenom', '')}".strip()
            cards.append(ft.Container(
                bgcolor=FIELD, border=ft.border.all(1, clr), border_radius=8, padding=10,
                content=ft.Row([
                    ft.Container(
                        width=40, height=40, bgcolor=clr, border_radius=8,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(f"J-{jours}" if jours >= 0 else "EXP", color="#FFFFFF", size=10, weight=ft.FontWeight.BOLD),
                    ),
                    ft.Column([
                        ft.Text(emp_name, color=DARK_TEXT, size=11, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{row.get('type_epi', '')} — {row.get('epi_nom', '')}", color=DARK_MUTED, size=10),
                        ft.Text(f"Exp: {row.get('date_expiration', '—')} · {row.get('fonction', '')} · {row.get('site', '')}", color=DARK_MUTED, size=9),
                    ], spacing=2, expand=True),
                    ft.ElevatedButton(
                        "Renouveler", icon=ft.Icons.AUTORENEW_OUTLINED, bgcolor=clr, color="#FFFFFF",
                        on_click=lambda ev, r=row: _renew_assignment(r),
                    ),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))
        renewal_area.controls = [
            ft.Text(f"{len(rows)} EPI à renouveler (≤ 30 jours)", color=WARNING, size=11, weight=ft.FontWeight.W_500),
            ft.Column(controls=cards, spacing=6, tight=True),
        ]
        try:
            renewal_area.update()
        except RuntimeError:
            pass

    def _renew_assignment(row: dict[str, Any]) -> None:
        emp_name = f"{row.get('nom', '')} {row.get('prenom', '')}".strip()
        confirm_action(
            page,
            "Renouveler l'EPI",
            f"L'affectation actuelle sera clôturée et un nouvel EPI sera attribué à {emp_name}.",
            lambda: _do_renew(row),
            confirm_label="Renouveler",
        )

    def _do_renew(row: dict[str, Any]) -> None:
        try:
            return_ppe_assignment(int(row["id_affectation"]), status="retourne")
            assign_multiple_ppe(
                row["employe_id"],
                [{"epi_id": row["epi_id"], "quantite": row["quantite"]}],
                today_iso(),
                "Renouvellement automatique",
            )
            notify(f"EPI renouvelé pour {row.get('nom','')} {row.get('prenom','')}.", SUCCESS)
            render_renewal_panel()
            refresh_ppe_alerts()
            _update()
        except Exception as exc:
            notify(f"Erreur renouvellement : {exc}", DANGER)
            _update()

    # ── Multi-employee selector ────────────────────────────────────────────────

    def _update_selected_count() -> None:
        selected_count_text.value = f"{len(selected_employees)} employé(s) sélectionné(s)"
        try:
            selected_count_text.update()
        except RuntimeError:
            pass

    def render_employee_list(e: Any = None) -> None:
        search = str(emp_search_field.value or "").strip().lower()
        visible: list[ft.Control] = []
        for opt in employee_options_cache:
            label = str(opt.get("label") or "")
            if search and search not in label.lower():
                continue
            eid = int(opt["value"])
            is_sel = eid in selected_employees
            if eid not in employee_checkboxes:
                cb = ft.Checkbox(
                    label=label, value=is_sel, active_color=PRIMARY,
                    label_style=ft.TextStyle(color=DARK_TEXT, size=11),
                    on_change=lambda ev, e_id=eid, lbl=label: _toggle_employee(e_id, lbl, ev.control.value),
                )
                employee_checkboxes[eid] = cb
            else:
                employee_checkboxes[eid].value = is_sel
            visible.append(ft.Container(
                bgcolor="#142B45" if is_sel else FIELD,
                border=ft.border.all(1, PRIMARY if is_sel else DARK_BORDER),
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                content=employee_checkboxes[eid],
            ))
        employee_list_area.controls = visible or [
            ft.Text("Aucun employé correspondant.", color=DARK_MUTED, size=11, italic=True)
        ]
        try:
            employee_list_area.update()
        except RuntimeError:
            pass

    emp_search_field.on_change = render_employee_list

    def _toggle_employee(emp_id: int, label: str, checked: bool) -> None:
        if checked:
            parts = str(label).split(" - ")
            badge = parts[-1].strip() if len(parts) > 1 else ""
            name_part = parts[0].strip() if parts else label
            name_tokens = name_part.split(" ", 1)
            selected_employees[emp_id] = {
                "id_employe": emp_id,
                "nom": name_tokens[0] if name_tokens else "",
                "prenom": name_tokens[1] if len(name_tokens) > 1 else "",
                "matricule": "", "badge": badge, "fonction": "", "site": "",
            }
        else:
            selected_employees.pop(emp_id, None)
        render_employee_list()
        _update_selected_count()

    def _select_all_employees(e: Any = None) -> None:
        search = str(emp_search_field.value or "").strip().lower()
        for opt in employee_options_cache:
            label = str(opt.get("label") or "")
            if search and search not in label.lower():
                continue
            eid = int(opt["value"])
            parts = str(label).split(" - ")
            badge = parts[-1].strip() if len(parts) > 1 else ""
            name_part = parts[0].strip() if parts else label
            name_tokens = name_part.split(" ", 1)
            selected_employees[eid] = {
                "id_employe": eid,
                "nom": name_tokens[0] if name_tokens else "",
                "prenom": name_tokens[1] if len(name_tokens) > 1 else "",
                "matricule": "", "badge": badge, "fonction": "", "site": "",
            }
        render_employee_list()
        _update_selected_count()

    def _deselect_all_employees(e: Any = None) -> None:
        selected_employees.clear()
        employee_checkboxes.clear()
        render_employee_list()
        _update_selected_count()

    def _do_batch_assign(e: Any = None) -> None:
        if not selected_employees:
            notify("Sélectionnez au moins un employé.", DANGER)
            _update()
            return
        items = list(assignment_basket)
        if not items:
            notify("Ajoutez au moins un EPI au panier.", DANGER)
            _update()
            return
        errors: list[str] = []
        success_count = 0
        for emp in list(selected_employees.values()):
            try:
                assign_multiple_ppe(emp["id_employe"], items, assignment_date_field.value, str(assignment_observation_field.value or ""))
                success_count += 1
            except Exception as exc:
                errors.append(f"{emp['nom']} {emp['prenom']}: {exc}")
        msg = f"Dotation effectuée pour {success_count} employé(s)."
        if errors:
            msg = f"{success_count} OK — Erreurs: {'; '.join(errors[:2])}"
        notify(msg, SUCCESS if not errors else WARNING)
        assignment_basket.clear()
        render_assignment_basket()
        refresh_ppe_alerts()
        render_dotation_list()
        _update()

    def _generate_fiche(e: Any = None) -> None:
        if not selected_employees:
            notify("Sélectionnez au moins un employé.", DANGER)
            _update()
            return
        items_for_pdf = [
            {
                "label": item["label"],
                "type_epi": str(item["label"]).split(" - ")[0] if " - " in str(item["label"]) else item["label"],
                "designation": item["label"], "epi_nom": item["label"],
                "quantite": item["quantite"], "taille": "", "norme": "", "etat": "neuf",
                "date_remise": item.get("date_remise") or assignment_date_field.value or today_iso(),
            }
            for item in assignment_basket
        ]
        if not items_for_pdf:
            notify("Ajoutez des EPI au panier avant de générer la fiche.", DANGER)
            _update()
            return
        try:
            path = export_ppe_dotation_sheet_pdf(
                list(selected_employees.values()), items_for_pdf,
                assignment_date_field.value or today_iso(),
                str(issued_by_field.value or ""),
                str(assignment_observation_field.value or ""),
            )
            open_dotation_file(path)
            notify(f"Fiche de dotation générée : {path.name}", SUCCESS)
            _update()
        except Exception as exc:
            notify(f"Erreur génération fiche : {exc}", DANGER)
            _update()

    def _do_batch_assign_and_fiche(e: Any = None) -> None:
        if not selected_employees or not assignment_basket:
            notify("Sélectionnez des employés et ajoutez des EPI au panier.", DANGER)
            _update()
            return
        items_for_pdf = [
            {
                "label": item["label"],
                "type_epi": str(item["label"]).split(" - ")[0] if " - " in str(item["label"]) else item["label"],
                "designation": item["label"], "epi_nom": item["label"],
                "quantite": item["quantite"], "taille": "", "norme": "", "etat": "neuf",
                "date_remise": item.get("date_remise") or assignment_date_field.value or today_iso(),
            }
            for item in assignment_basket
        ]
        _do_batch_assign(e)
        if items_for_pdf and selected_employees:
            try:
                path = export_ppe_dotation_sheet_pdf(
                    list(selected_employees.values()), items_for_pdf,
                    assignment_date_field.value or today_iso(),
                    str(issued_by_field.value or ""),
                    str(assignment_observation_field.value or ""),
                )
                open_dotation_file(path)
                notify(f"Fiche de dotation générée : {path.name}", SUCCESS)
                _update()
            except Exception as exc:
                notify(f"Dotation OK mais erreur fiche : {exc}", WARNING)
                _update()

    def _generate_employee_fiche(emp_data: dict[str, Any]) -> None:
        epi_list = emp_data.get("epi_list", [])
        if not epi_list:
            notify("Cet employé n'a aucun EPI actif à imprimer.", WARNING)
            _update()
            return
        items_for_pdf = [
            {
                "label": f"{item.get('type_epi', '')} - {item.get('epi_nom', '')}",
                "type_epi": item.get("type_epi", ""),
                "designation": item.get("epi_nom", ""),
                "epi_nom": item.get("epi_nom", ""),
                "quantite": item.get("quantite", 1),
                "taille": item.get("taille", "—"),
                "norme": item.get("norme", "—"),
                "etat": item.get("etat", ""),
                "date_remise": item.get("date_remise", ""),
                "date_expiration": item.get("date_expiration", ""),
            }
            for item in epi_list
        ]
        emp_for_pdf = [{
            "nom": emp_data.get("nom", ""),
            "prenom": emp_data.get("prenom", ""),
            "matricule": emp_data.get("matricule", ""),
            "badge": emp_data.get("badge", ""),
            "fonction": emp_data.get("fonction", ""),
            "site": emp_data.get("site", ""),
        }]
        try:
            path = export_ppe_dotation_sheet_pdf(
                emp_for_pdf, items_for_pdf,
                emp_data.get("derniere_dotation") or today_iso(), "", "",
            )
            open_dotation_file(path)
            notify(f"Fiche générée : {path.name}", SUCCESS)
            _update()
        except Exception as exc:
            notify(f"Erreur fiche : {exc}", DANGER)
            _update()

    def render_dotation_list(e: Any = None) -> None:
        try:
            employees = get_employees_dotation_list()
        except Exception:
            employees = []
        if not employees:
            dotation_list_area.controls = [
                ft.Text("Aucune dotation active enregistrée.", color=DARK_MUTED, size=12, italic=True)
            ]
            try:
                dotation_list_area.update()
            except RuntimeError:
                pass
            return

        total = len(employees)
        max_page = max(0, (total - 1) // PAGE_SIZE)
        state["page"] = max(0, min(max_page, state["page"]))
        start = state["page"] * PAGE_SIZE
        page_employees = employees[start : start + PAGE_SIZE]

        col_style = ft.TextStyle(color=PRIMARY, size=11, weight=ft.FontWeight.BOLD)
        rows: list[ft.DataRow] = []
        for emp in page_employees:
            epi_list = emp.get("epi_list", [])
            epi_summary = ", ".join(f"{item['type_epi']} ×{item['quantite']}" for item in epi_list[:3])
            if len(epi_list) > 3:
                epi_summary += f" +{len(epi_list) - 3} autre(s)"
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Column([
                    ft.Text(f"{emp.get('nom', '')} {emp.get('prenom', '')}".strip(), color=DARK_TEXT, size=11, weight=ft.FontWeight.W_600),
                    ft.Text(emp.get("matricule") or "—", color=DARK_MUTED, size=9),
                ], spacing=1)),
                ft.DataCell(ft.Text(emp.get("badge") or "—", color=DARK_MUTED, size=10)),
                ft.DataCell(ft.Column([
                    ft.Text(emp.get("fonction") or "—", color=DARK_TEXT, size=10),
                    ft.Text(emp.get("site") or "—", color=DARK_MUTED, size=9),
                ], spacing=1)),
                ft.DataCell(ft.Row([
                    ft.Container(
                        bgcolor=PRIMARY, border_radius=12,
                        padding=ft.padding.symmetric(horizontal=7, vertical=2),
                        content=ft.Text(str(emp.get("nb_epi", 0)), color="#FFFFFF", size=10, weight=ft.FontWeight.BOLD),
                    ),
                    ft.Text(epi_summary, color=DARK_MUTED, size=10, expand=True, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)),
                ft.DataCell(ft.Text(emp.get("derniere_dotation") or "—", color=DARK_MUTED, size=10)),
                ft.DataCell(ft.IconButton(
                    icon=ft.Icons.PICTURE_AS_PDF_OUTLINED, icon_color=WARNING, icon_size=16,
                    tooltip="Générer fiche de dotation PDF",
                    on_click=lambda ev, em=emp: _generate_employee_fiche(em),
                )),
                ft.DataCell(ft.IconButton(
                    icon=ft.Icons.SETTINGS_BACKUP_RESTORE_OUTLINED, icon_color=DANGER, icon_size=16,
                    tooltip="Retour total — clôturer tous les EPI de cet employé",
                    on_click=lambda ev, em=emp: _close_all_for_employee(
                        int(em.get("id_employe", 0)),
                        f"{em.get('nom', '')} {em.get('prenom', '')}".strip(),
                    ),
                )),
            ]))
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Employé", style=col_style)),
                ft.DataColumn(ft.Text("Badge", style=col_style)),
                ft.DataColumn(ft.Text("Fonction / Site", style=col_style)),
                ft.DataColumn(ft.Text("EPI actifs", style=col_style)),
                ft.DataColumn(ft.Text("Dernière dotation", style=col_style)),
                ft.DataColumn(ft.Text("Fiche", style=col_style)),
                ft.DataColumn(ft.Text("Retour", style=col_style)),
            ],
            rows=rows,
            heading_row_color={ft.ControlState.DEFAULT: "#142B45"},
            data_row_color={ft.ControlState.DEFAULT: CARD},
            border=ft.border.all(1, DARK_BORDER),
            border_radius=8,
            column_spacing=12,
            data_row_min_height=52,
        )
        dotation_list_area.controls = [
            ft.Container(bgcolor=CARD, border_radius=8, content=ft.Row(controls=[table], scroll=ft.ScrollMode.AUTO, tight=True)),
            pagination_row(
                current_page=state["page"],
                max_page=max_page,
                total=total,
                shown_start=start + 1 if page_employees else 0,
                shown_end=start + len(page_employees),
                item_label="employé(s)",
                on_prev=lambda: (state.__setitem__("page", state["page"] - 1), render_dotation_list()),
                on_next=lambda: (state.__setitem__("page", state["page"] + 1), render_dotation_list()),
                on_page=lambda p: (state.__setitem__("page", p), render_dotation_list()),
            ),
        ]
        try:
            dotation_list_area.update()
        except RuntimeError:
            pass

    def save_assignment(event: ft.ControlEvent | None = None) -> None:
        try:
            items = list(assignment_basket) or [
                {"epi_id": assignment_item_field.value, "quantite": assignment_quantity_field.value}
            ]
            assignment_ids = assign_multiple_ppe(
                assignment_employee_field.value, items,
                assignment_date_field.value, assignment_observation_field.value,
            )
            assignment_basket.clear()
            render_assignment_basket()
            notify(f"Dotation enregistree: {len(assignment_ids)} EPI attribue(s).", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def close_assignment(assignment_id: int, close_status: str) -> None:
        confirm_action(
            page, "Cloturer l'affectation EPI",
            "Cette affectation sera marquee comme retournee ou cloturee.",
            lambda: _close_assignment(assignment_id, close_status),
            confirm_label="Cloturer",
        )

    def _close_assignment(assignment_id: int, close_status: str) -> None:
        try:
            return_ppe_assignment(assignment_id, status=close_status)
            notify("Affectation cloturee.", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def save_requirement(event: ft.ControlEvent | None = None) -> None:
        try:
            save_ppe_requirement({
                "fonction_id": requirement_function_field.value,
                "type_epi_id": requirement_type_field.value,
                "quantite": requirement_quantity_field.value,
                "obligatoire": requirement_mandatory_field.value,
            })
            notify("Dotation obligatoire mise a jour.", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def remove_requirement(requirement_id: int) -> None:
        confirm_action(
            page, "Supprimer la dotation obligatoire",
            "Cette regle de dotation EPI sera supprimee.",
            lambda: _remove_requirement(requirement_id),
            confirm_label="Supprimer", danger=True,
        )

    def _remove_requirement(requirement_id: int) -> None:
        try:
            delete_ppe_requirement(requirement_id)
            notify("Dotation obligatoire supprimee.", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def save_inspection(event: ft.ControlEvent | None = None) -> None:
        try:
            record_ppe_inspection({
                "epi_id": inspection_item_field.value,
                "date_inspection": inspection_date_field.value,
                "statut": inspection_status_field.value,
                "prochaine_inspection": inspection_next_field.value,
                "inspecteur": inspection_inspector_field.value,
                "observations": inspection_observation_field.value,
            })
            inspection_observation_field.value = ""
            notify("Inspection EPI enregistree.", SUCCESS)
            refresh()
        except Exception as exc:
            notify(str(exc), DANGER)
            _update()

    def export_inventory(event: ft.ControlEvent | None = None) -> None:
        output = export_ppe_inventory_xls()
        notify(f"Export Gestion des EPI cree: {output}", SUCCESS)
        _update()

    def export_equipped_employees(event: ft.ControlEvent | None = None) -> None:
        output = export_ppe_equipped_employees_xlsx()
        notify(f"Liste detaillee des employes dotes creee: {output}", SUCCESS)
        _update()

    def export_compliance(event: ft.ControlEvent | None = None) -> None:
        output = export_ppe_compliance_xlsx()
        notify(f"Export conformite EPI cree: {output}", SUCCESS)
        _update()

    def export_inspections(event: ft.ControlEvent | None = None) -> None:
        output = export_ppe_inspections_xlsx()
        notify(f"Export inspections EPI cree: {output}", SUCCESS)
        _update()

    # ── Data render functions ──────────────────────────────────────────────────

    def render_summary() -> None:
        summary = get_ppe_summary()
        summary_row.controls = [
            _summary_chip("Total EPI", summary["items"], PRIMARY, ft.Icons.INVENTORY_2_OUTLINED),
            _summary_chip("Stock total", summary["stock_total"], SUCCESS, ft.Icons.WAREHOUSE_OUTLINED),
            _summary_chip("EPI affectes", summary["assigned"], PRIMARY, ft.Icons.ASSIGNMENT_IND_OUTLINED),
            _summary_chip("Disponibles", summary["available"], SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
            _summary_chip("Stock bas", summary["low_stock"], DANGER if summary["low_stock"] else SUCCESS, ft.Icons.REPORT_PROBLEM_OUTLINED),
            _summary_chip("EPI expires", summary["expired"], DANGER if summary["expired"] else SUCCESS, ft.Icons.EVENT_BUSY_OUTLINED),
            _summary_chip("Inspections retard", summary["overdue_inspections"], DANGER if summary["overdue_inspections"] else SUCCESS, ft.Icons.EVENT_REPEAT_OUTLINED),
            _summary_chip("Conformite", f"{summary['compliance_rate']}%", SUCCESS if summary["compliance_rate"] == 100 else WARNING, ft.Icons.FACT_CHECK_OUTLINED),
        ]

    def render_catalog() -> None:
        rows = list_ppe_items(search=str(search_field.value or ""))
        catalog_area.controls = [
            ft.Row(
                controls=[
                    ft.Text(f"Catalogue ({len(rows)} EPI)", size=14, weight=ft.FontWeight.BOLD, color=DARK_TEXT, expand=True),
                    status,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    professional_data_table(
                        columns=[
                            ft.DataColumn(ft.Text("Type")),
                            ft.DataColumn(ft.Text("EPI")),
                            ft.DataColumn(ft.Text("Taille")),
                            ft.DataColumn(ft.Text("Etat")),
                            ft.DataColumn(ft.Text("Stock")),
                            ft.DataColumn(ft.Text("Seuil")),
                            ft.DataColumn(ft.Text("Alerte")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=[
                            ft.DataRow(cells=[
                                ft.DataCell(ft.Text(str(row.get("type_epi") or "-"), color=DARK_MUTED)),
                                ft.DataCell(ft.Text(str(row.get("nom") or "-"), color=DARK_TEXT, weight=ft.FontWeight.BOLD)),
                                ft.DataCell(ft.Text(str(row.get("taille") or "-"), color=DARK_MUTED)),
                                ft.DataCell(ft.Text(str(row.get("etat") or "-"), color=DARK_MUTED)),
                                ft.DataCell(ft.Text(str(row.get("quantite_disponible") or 0), color=SUCCESS if not row.get("stock_bas") else DANGER, weight=ft.FontWeight.BOLD)),
                                ft.DataCell(ft.Text(str(row.get("seuil_minimum") or 0), color=DARK_MUTED)),
                                ft.DataCell(_status_badge("Stock bas", DANGER) if row.get("stock_bas") else _status_badge("OK", SUCCESS)),
                                ft.DataCell(ft.Row([
                                    ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, tooltip="Modifier", icon_color=PRIMARY, on_click=lambda ev, item=row: edit_item(item)),
                                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="Supprimer", icon_color=DANGER, on_click=lambda ev, iid=row["id_epi"]: delete_item(int(iid))),
                                ], spacing=0)),
                            ])
                            for row in rows
                        ],
                        bgcolor=FIELD,
                        border=ft.border.all(1, DARK_BORDER),
                        border_radius=8,
                        heading_row_color="#142B45",
                        horizontal_lines=ft.BorderSide(1, DARK_BORDER),
                        vertical_lines=ft.BorderSide(1, DARK_BORDER),
                        heading_text_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
                        data_text_style=ft.TextStyle(size=11, color=DARK_MUTED),
                        data_row_color={
                            ft.ControlState.HOVERED: "#142B45",
                            ft.ControlState.PRESSED: "#17304A",
                            ft.ControlState.SELECTED: "#123B46",
                        },
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        ]

    def render_movements() -> None:
        rows = list_stock_movements()
        sel_item = str(movement_filter_item.value or "")
        sel_type = str(movement_filter_type.value or "")
        emp_q = str(movement_filter_employee.value or "").strip().lower()
        sel_date = str(movement_filter_date.value or "").strip()
        rows = [
            r for r in rows
            if (not sel_item or str(r.get("epi_id")) == sel_item)
            and (not sel_type or str(r.get("type_mouvement")) == sel_type)
            and (not emp_q or emp_q in f"{r.get('employe_nom') or ''} {r.get('employe_prenom') or ''}".lower())
            and (not sel_date or str(r.get("date_mouvement") or "").startswith(sel_date))
        ]
        movement_area.controls = [
            ft.Text(f"Mouvements ({len(rows)})", size=14, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
            ft.Column(
                controls=[
                    ft.Container(
                        bgcolor=FIELD, border=ft.border.all(1, DARK_BORDER), border_radius=8, padding=9,
                        content=ft.Row([
                            ft.Text(str(r.get("date_mouvement") or "-"), color=DARK_MUTED, size=9),
                            _status_badge(str(r.get("type_mouvement") or "-").title(), SUCCESS if r.get("type_mouvement") == "entree" else WARNING),
                            ft.Text(f"{r.get('type_epi') or '-'} - {r.get('epi') or '-'}", color=DARK_TEXT, size=10, weight=ft.FontWeight.BOLD),
                            ft.Text(f"x{r.get('quantite') or 0}", color=PRIMARY, size=10),
                            ft.Text(f"{r.get('employe_nom') or ''} {r.get('employe_prenom') or ''}".strip() or "-", color=DARK_MUTED, size=9),
                            ft.Text(str(r.get("motif") or "-"), color=DARK_MUTED, size=9, expand=True),
                        ], spacing=8),
                    )
                    for r in rows[:30]
                ],
                spacing=4,
            ) if rows else ft.Text("Aucun mouvement correspondant.", size=12, color=MUTED),
        ]

    def render_assignments() -> None:
        rows = list_ppe_assignments(active_only=True)
        assignment_area.controls = [
            ft.Text("Affectations en service", size=14, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
            ft.Column(
                controls=[
                    ft.Row([
                        ft.Text(
                            f"{r.get('nom') or '-'} {r.get('prenom') or ''} | {r['type_epi']} - {r['epi']} x{r['quantite']} | {r['date_remise']}",
                            size=12, color=DARK_TEXT, expand=True,
                        ),
                        ft.IconButton(icon=ft.Icons.KEYBOARD_RETURN_OUTLINED, tooltip="Retour stock", icon_color=SUCCESS, on_click=lambda ev, aid=r["id_affectation"]: close_assignment(aid, "retourne")),
                        ft.IconButton(icon=ft.Icons.BLOCK_OUTLINED, tooltip="Perdu", icon_color=DANGER, on_click=lambda ev, aid=r["id_affectation"]: close_assignment(aid, "perdu")),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                    for r in rows[:12]
                ],
                spacing=4,
            ) if rows else ft.Text("Aucune affectation en service.", size=12, color=MUTED),
        ]

    def render_requirements() -> None:
        rows = list_ppe_requirements()
        compliance = list_ppe_compliance()
        missing = [r for r in compliance if r.get("statut") == "manquant"]
        requirement_area.controls = [
            ft.Text("Dotation obligatoire par fonction", size=14, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
            ft.Column(
                controls=[
                    ft.Row([
                        ft.Text(
                            f"{r['fonction']} | {r['type_epi']} x{r['quantite']} | {'obligatoire' if r['obligatoire'] else 'optionnel'}",
                            size=12, color=DARK_TEXT, expand=True,
                        ),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="Supprimer", icon_color=DANGER, on_click=lambda ev, rid=r["id_requis"]: remove_requirement(int(rid))),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
                    for r in rows
                ],
                spacing=4,
            ) if rows else ft.Text("Aucune dotation obligatoire parametree.", size=12, color=MUTED),
        ]
        compliance_area.controls = [
            ft.Text(f"Conformite employes ({len(missing)} manquant)", size=14, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
            ft.Column(
                controls=[
                    ft.Text(
                        f"{r.get('nom') or '-'} {r.get('prenom') or ''} | {r['fonction']} | {r['type_epi']}: {r['affecte']}/{r['requis']} - {r['statut']}",
                        size=12,
                        color=DANGER if r.get("statut") == "manquant" else SUCCESS,
                    )
                    for r in compliance[:12]
                ],
                spacing=4,
            ) if compliance else ft.Text("La conformite apparaitra apres parametrage.", size=12, color=MUTED),
        ]

    def render_inspections() -> None:
        rows = list_ppe_inspections()
        inspection_area.controls = [
            ft.Text("Dernieres inspections", size=14, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
            ft.Column(
                controls=[
                    ft.Text(
                        f"{r['date_inspection']} | {r['type_epi']} - {r['epi']} | {r['statut']} | prochaine: {r.get('prochaine_inspection') or '-'}",
                        size=12,
                        color=DANGER if r.get("statut") in ("endommage", "hors_service") else TEXT,
                    )
                    for r in rows[:10]
                ],
                spacing=4,
            ) if rows else ft.Text("Aucune inspection enregistree.", size=12, color=MUTED),
        ]

    def render_alerts() -> None:
        rows = refresh_ppe_alerts()
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(str(row.get("categorie") or "autres"), []).append(row)
        grouped_controls = [
            ft.ExpansionTile(
                title=ft.Text(cat.replace("_", " ").title(), color=DARK_TEXT, weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(f"{len(items)} alerte(s)", color=DARK_MUTED, size=9),
                leading=ft.Icons.WARNING_AMBER_OUTLINED,
                expanded=True,
                controls=[_alert_row(item) for item in items],
            )
            for cat, items in grouped.items()
        ]
        alert_area.controls = [
            ft.Text("Alertes EPI automatisées", size=14, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
            *(grouped_controls if rows else [ft.Text("Aucune alerte EPI ouverte.", size=12, color=SUCCESS)]),
        ]

    def render_compliance_summary() -> None:
        rows = list_ppe_employee_compliance_summary()
        compliance_summary_area.controls = [
            _compliance_employee_row(r) for r in rows
        ] or [ft.Text("Aucune regle obligatoire configuree.", color=DARK_MUTED, size=10)]

    # ── Employee cards + fiche (Tab 2) ─────────────────────────────────────────

    def _emp_card(row: dict[str, Any]) -> ft.Control:
        pct = int(row.get("pourcentage") or 0)
        color = SUCCESS if pct >= 80 else WARNING if pct >= 50 else DANGER
        name = f"{row.get('nom') or ''} {row.get('prenom') or ''}".strip()
        initials = "".join(p[0].upper() for p in name.split()[:2]) if name else "?"

        def on_select(e, r=row):
            state["selected_emp"] = r
            render_tab2()
            _update()

        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4, "lg": 3},
            bgcolor=CARD,
            border=ft.border.all(2, color),
            border_radius=10,
            padding=14,
            on_click=on_select,
            ink=True,
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        width=38, height=38,
                        bgcolor=color + "33",
                        border_radius=19,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(initials, size=13, weight=ft.FontWeight.BOLD, color=color),
                    ),
                    ft.Column([
                        ft.Text(name, size=11, color=DARK_TEXT, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(str(row.get("fonction") or "-"), size=9, color=DARK_MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(str(row.get("site") or "-"), size=9, color=DARK_MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=1, expand=True),
                ], spacing=8),
                ft.Row([
                    ft.Container(
                        bgcolor=color + "22",
                        border=ft.border.all(1, color),
                        border_radius=12,
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        content=ft.Text(f"{pct}%", size=11, color=color, weight=ft.FontWeight.BOLD),
                    ),
                    ft.Text(f"{row.get('recus', 0)}/{row.get('requis', 0)} EPI", size=10, color=DARK_MUTED),
                ], spacing=6),
            ], spacing=8),
        )

    def render_tab2() -> None:
        if state["selected_emp"] is None:
            _render_emp_browser()
        else:
            _render_emp_fiche(state["selected_emp"])

    def _render_emp_browser() -> None:
        try:
            rows = list_ppe_employee_compliance_summary()
        except Exception:
            rows = []

        total = len(rows)
        conformes = sum(1 for r in rows if str(r.get("statut")) == "conforme")

        kpi_row = ft.Row([
            _info_chip(ft.Icons.GROUPS_OUTLINED, "Employés avec EPI", str(total)),
            _info_chip(ft.Icons.CHECK_CIRCLE_OUTLINE, "Conformes", str(conformes), SUCCESS),
            _info_chip(ft.Icons.WARNING_AMBER_OUTLINED, "Non conformes", str(total - conformes), DANGER if total - conformes else DARK_MUTED),
        ], spacing=10, wrap=True)

        grid_col = ft.Column(spacing=0)

        def _filter(query: str = "") -> None:
            q = query.strip().lower()
            filtered = [
                r for r in rows
                if not q
                or q in f"{r.get('nom','')} {r.get('prenom','')}".lower()
                or q in str(r.get("fonction", "")).lower()
                or q in str(r.get("site", "")).lower()
            ]
            grid_col.controls = [
                ft.ResponsiveRow(controls=[_emp_card(r) for r in filtered], spacing=10, run_spacing=10)
            ] if filtered else [ft.Text("Aucun employé trouvé.", color=DARK_MUTED, italic=True, size=12)]
            try:
                grid_col.update()
            except RuntimeError:
                pass

        search_tf = ft.TextField(
            label="Rechercher (nom, fonction, site)",
            prefix_icon=ft.Icons.SEARCH,
            bgcolor=FIELD, color=DARK_TEXT,
            border_color=DARK_BORDER, focused_border_color=PRIMARY,
            label_style=ft.TextStyle(color=DARK_MUTED),
            width=320,
            on_change=lambda e: _filter(e.control.value),
        )
        _filter()

        tab2_col.controls = [
            ft.Container(
                bgcolor=CARD, border=ft.border.all(1, DARK_BORDER), border_radius=8, padding=14,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.BADGE_OUTLINED, color=PRIMARY, size=20),
                        ft.Text("Conformité EPI par employé", size=16, weight=ft.FontWeight.BOLD, color=DARK_TEXT, expand=True),
                        ft.OutlinedButton(
                            "Actualiser", icon=ft.Icons.REFRESH,
                            on_click=lambda e: (render_tab2(), _update()),
                            style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: DARK_MUTED}, side=ft.BorderSide(1, DARK_BORDER)),
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    kpi_row,
                    search_tf,
                ], spacing=10),
            ),
            grid_col,
        ]
        try:
            tab2_col.update()
        except RuntimeError:
            pass

    def _render_emp_fiche(row: dict[str, Any]) -> None:
        emp_id = row.get("id_employe") or row.get("employe_id")
        name = f"{row.get('nom') or ''} {row.get('prenom') or ''}".strip()
        initials = "".join(p[0].upper() for p in name.split()[:2]) if name else "?"
        pct = int(row.get("pourcentage") or 0)
        color = SUCCESS if pct >= 80 else WARNING if pct >= 50 else DANGER

        profile: dict[str, Any] = {}
        epi_active: list[dict[str, Any]] = []
        try:
            if emp_id:
                profile = get_employee_ppe_profile(emp_id)
                all_emp = get_employees_dotation_list()
                match = next((e for e in all_emp if str(e.get("id_employe")) == str(emp_id)), None)
                if match:
                    epi_active = match.get("epi_list", [])
        except Exception:
            pass

        requirements = profile.get("requirements", [])
        manquants = [r for r in requirements if str(r.get("statut")) in ("manquant", "stock_insuffisant")]

        def go_back(e: Any = None) -> None:
            state["selected_emp"] = None
            render_tab2()
            _update()

        # Header card
        header = ft.Container(
            bgcolor=CARD, border=ft.border.all(2, color), border_radius=10, padding=16,
            content=ft.Row([
                ft.Container(
                    width=54, height=54, bgcolor=color + "33", border_radius=27,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(initials, size=20, weight=ft.FontWeight.BOLD, color=color),
                ),
                ft.Column([
                    ft.Text(name, size=16, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
                    ft.Text(
                        f"{profile.get('fonction') or row.get('fonction') or '-'} · {profile.get('site') or row.get('site') or '-'}",
                        size=11, color=DARK_MUTED,
                    ),
                    ft.Text(f"Badge : {profile.get('numero_badge') or '—'}", size=10, color=DARK_MUTED),
                ], spacing=2, expand=True),
                ft.Container(
                    bgcolor=color + "22", border=ft.border.all(1, color), border_radius=12,
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    content=ft.Column([
                        ft.Text(f"{pct}%", size=22, weight=ft.FontWeight.BOLD, color=color),
                        ft.Text("Conformité", size=9, color=DARK_MUTED),
                    ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ),
            ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

        kpi = ft.Row([
            _info_chip(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, "EPI actifs", str(len(epi_active)), PRIMARY),
            _info_chip(ft.Icons.WARNING_AMBER_OUTLINED, "Manquants", str(len(manquants)), DANGER if manquants else DARK_MUTED),
            _info_chip(ft.Icons.RULE_OUTLINED, "Types requis", str(len(requirements)), DARK_MUTED),
        ], spacing=10, wrap=True)

        # EPI actifs
        _S = {"en_service": SUCCESS, "retourne": DARK_MUTED, "perdu": DANGER, "deteriore": WARNING, "vole": DANGER}
        if epi_active:
            epi_list_ctrl = ft.Column([
                ft.Container(
                    bgcolor=FIELD, border=ft.border.all(1, DARK_BORDER), border_radius=8, padding=10,
                    content=ft.Row([
                        ft.Icon(ft.Icons.SECURITY_OUTLINED, color=PRIMARY, size=16),
                        ft.Column([
                            ft.Text(f"{item.get('type_epi', '')}: {item.get('epi_nom', '')}", size=11, color=DARK_TEXT, weight=ft.FontWeight.W_600),
                            ft.Text(
                                f"×{item.get('quantite',1)}  ·  Taille: {item.get('taille','—')}  ·  Norme: {item.get('norme','—')}  ·  Exp: {item.get('date_expiration','—')}",
                                size=9, color=DARK_MUTED,
                            ),
                        ], spacing=2, expand=True),
                        _status_badge(str(item.get("statut", "")).replace("_", " ").title(), _S.get(str(item.get("statut", "")), DARK_MUTED)),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
                for item in epi_active
            ], spacing=6)
        else:
            epi_list_ctrl = ft.Text("Aucun EPI actif enregistré.", color=DARK_MUTED, italic=True, size=11)

        # Manquants
        if manquants:
            manq_ctrl = ft.Column([_required_ppe_row(r) for r in manquants], spacing=6)
        else:
            manq_ctrl = ft.Text("Tous les EPI requis sont attribués.", color=SUCCESS, size=11)

        # Pre-fill quick dotation employee
        if emp_id and assignment_employee_field.options:
            for opt in assignment_employee_field.options:
                if str(opt.key) == str(emp_id):
                    assignment_employee_field.value = str(emp_id)
                    break

        def _quick_assign(e: Any = None) -> None:
            if not assignment_basket:
                notify("Ajoutez au moins un EPI au panier.", DANGER)
                _update()
                return
            try:
                ids = assign_multiple_ppe(
                    emp_id, list(assignment_basket),
                    assignment_date_field.value,
                    str(assignment_observation_field.value or ""),
                )
                assignment_basket.clear()
                render_assignment_basket()
                notify(f"{len(ids)} EPI attribué(s).", SUCCESS)
                refresh_ppe_alerts()
                # Reload fiche with updated compliance row
                try:
                    updated_rows = list_ppe_employee_compliance_summary()
                    updated = next((r for r in updated_rows if str(r.get("id_employe")) == str(emp_id)), state["selected_emp"])
                    state["selected_emp"] = updated
                except Exception:
                    pass
                render_tab2()
                _update()
            except Exception as exc:
                notify(f"Erreur : {exc}", DANGER)
                _update()

        def _auto_assign(e: Any = None) -> None:
            try:
                ids = assign_required_ppe(emp_id, assignment_date_field.value, str(assignment_observation_field.value or ""))
                notify(f"Dotation automatique : {len(ids)} EPI attribué(s).", SUCCESS)
                refresh_ppe_alerts()
                try:
                    updated_rows = list_ppe_employee_compliance_summary()
                    updated = next((r for r in updated_rows if str(r.get("id_employe")) == str(emp_id)), state["selected_emp"])
                    state["selected_emp"] = updated
                except Exception:
                    pass
                render_tab2()
                _update()
            except Exception as exc:
                notify(f"Erreur : {exc}", DANGER)
                _update()

        quick_dotation = _panel("Dotation rapide", [
            ft.Text("Composez le panier EPI puis confirmez pour cet employé.", color=DARK_MUTED, size=10),
            ft.Row([
                assignment_item_field,
                assignment_quantity_field,
                ft.ElevatedButton("Ajouter au panier", icon=ft.Icons.ADD_SHOPPING_CART_OUTLINED, on_click=add_assignment_to_basket, bgcolor=PRIMARY, color="#FFFFFF"),
            ], spacing=10, wrap=True, vertical_alignment=ft.CrossAxisAlignment.END),
            assignment_basket_area,
            ft.Row([
                assignment_date_field,
                issued_by_field,
                ft.ElevatedButton("Confirmer dotation", icon=ft.Icons.DONE_ALL_OUTLINED, bgcolor=SUCCESS, color="#FFFFFF", on_click=_quick_assign),
                ft.OutlinedButton("Dotation auto", icon=ft.Icons.AUTO_FIX_HIGH_OUTLINED, on_click=_auto_assign,
                    style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: WARNING}, side=ft.BorderSide(1, WARNING))),
            ], spacing=10, wrap=True, vertical_alignment=ft.CrossAxisAlignment.END),
            status,
        ])

        # Historique inline
        fiche_hist_area = ft.Column(spacing=4, tight=True)
        try:
            if emp_id:
                hist_rows_data = get_employee_dotation_history(int(emp_id))
                if hist_rows_data:
                    fiche_hist_area.controls = [
                        ft.Container(
                            bgcolor=FIELD, border=ft.border.all(1, DARK_BORDER), border_radius=8, padding=8,
                            content=ft.Row([
                                ft.Text(str(r.get("date_remise", "—")), color=DARK_MUTED, size=9, width=95),
                                ft.Text(f"{r.get('type_epi','—')}: {r.get('epi_nom','—')}", size=10, color=DARK_TEXT, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(f"×{r.get('quantite',1)}", color=PRIMARY, size=10),
                                _status_badge(str(r.get("statut","")).replace("_"," ").title(), _S.get(str(r.get("statut","")), DARK_MUTED)),
                            ], spacing=8),
                        )
                        for r in hist_rows_data[:10]
                    ]
                else:
                    fiche_hist_area.controls = [ft.Text("Aucun historique.", color=DARK_MUTED, italic=True, size=11)]
        except Exception:
            fiche_hist_area.controls = [ft.Text("Historique indisponible.", color=DARK_MUTED, italic=True, size=11)]

        def gen_pdf(e: Any = None) -> None:
            _generate_employee_fiche({
                "nom": row.get("nom", ""),
                "prenom": row.get("prenom", ""),
                "matricule": row.get("matricule", ""),
                "badge": profile.get("numero_badge", ""),
                "fonction": row.get("fonction", ""),
                "site": row.get("site", ""),
                "epi_list": epi_active,
                "derniere_dotation": today_iso(),
            })

        tab2_col.controls = [
            ft.TextButton("← Retour à la liste", on_click=go_back, style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: DARK_MUTED})),
            header,
            kpi,
            _panel("EPI actifs", [epi_list_ctrl]),
            _panel("⚠  EPI manquants / insuffisants", [manq_ctrl]),
            quick_dotation,
            _panel("Historique des dotations (10 derniers)", [
                ft.Row(controls=[fiche_hist_area], scroll=ft.ScrollMode.AUTO),
            ]),
            ft.Row([
                ft.ElevatedButton("Fiche PDF", icon=ft.Icons.PICTURE_AS_PDF_OUTLINED, on_click=gen_pdf, bgcolor=WARNING, color="#FFFFFF"),
                ft.OutlinedButton(
                    "Retour EPI total", icon=ft.Icons.SETTINGS_BACKUP_RESTORE_OUTLINED,
                    on_click=lambda e: _close_all_for_employee(int(emp_id or 0), name),
                    style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: DANGER}, side=ft.BorderSide(1, DANGER)),
                ),
            ], spacing=10, wrap=True),
        ]
        try:
            tab2_col.update()
        except RuntimeError:
            pass

    # ── Tab 1: Vue d'ensemble ──────────────────────────────────────────────────

    def render_tab1() -> None:
        tab1_col.controls = [
            ft.Container(
                bgcolor=CARD, border=ft.border.all(1, DARK_BORDER), border_radius=8, padding=14,
                content=ft.Column([
                    ft.Text("Indicateurs clés", size=14, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
                    summary_row,
                ], spacing=10),
            ),
            _panel("Actions recommandées", [_recommendations_row()]),
            _panel("Alertes prioritaires", [alert_area]),
            _panel("Renouvellements à venir (≤ 30 jours)", [
                ft.OutlinedButton(
                    "Actualiser", icon=ft.Icons.REFRESH, on_click=render_renewal_panel,
                    style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: WARNING}, side=ft.BorderSide(1, WARNING)),
                ),
                renewal_area,
            ]),
        ]
        try:
            tab1_col.update()
        except RuntimeError:
            pass

    # ── Tab 3: Gestion EPI ─────────────────────────────────────────────────────

    def _step_header(num_color: str, label: str) -> ft.Control:
        return ft.Row([
            ft.Container(width=4, height=14, bgcolor=num_color, border_radius=2),
            ft.Text(label, color=DARK_TEXT, size=13, weight=ft.FontWeight.BOLD),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def render_tab3() -> None:
        sub = state["gestion_tab"]

        def _sub_btn(name: str, label: str, icon: str) -> ft.TextButton:
            sel = sub == name
            return ft.TextButton(
                label, icon=icon,
                on_click=lambda e, n=name: _switch_gestion(n),
                style=ft.ButtonStyle(
                    color="#FFFFFF" if sel else "#C7D4E3",
                    bgcolor=PRIMARY if sel else FIELD,
                    shape=ft.RoundedRectangleBorder(radius=7),
                ),
            )

        sub_nav = ft.Container(
            bgcolor="#0A1929",
            border=ft.border.all(1, DARK_BORDER),
            border_radius=7,
            padding=6,
            content=ft.Row([
                _sub_btn("catalog", "Catalogue EPI", ft.Icons.INVENTORY_2_OUTLINED),
                _sub_btn("mouvements", "Mouvements stock", ft.Icons.SWAP_HORIZ_OUTLINED),
                _sub_btn("inspections", "Inspections", ft.Icons.EVENT_REPEAT_OUTLINED),
                _sub_btn("conformite", "Conformité", ft.Icons.FACT_CHECK_OUTLINED),
                _sub_btn("dotation", "Dotation collective", ft.Icons.GROUP_ADD_OUTLINED),
            ], spacing=6, wrap=True),
        )

        if sub == "catalog":
            content: ft.Control = ft.Column([
                _panel("Enregistrement EPI", [
                    ft.Text("Type, désignation, quantité et seuil minimum suffisent.", color=DARK_MUTED, size=10),
                    ft.ResponsiveRow([
                        ft.Container(type_field, col={"xs": 12, "md": 3}),
                        ft.Container(item_name_field, col={"xs": 12, "md": 4}),
                        ft.Container(initial_quantity_field, col={"xs": 6, "md": 2}),
                        ft.Container(threshold_field, col={"xs": 6, "md": 2}),
                    ], spacing=10, run_spacing=10),
                    ft.ExpansionTile(
                        title=ft.Text("Options avancées", color=DARK_TEXT, weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text("Taille, norme, marque, modèle, état, expiration", color=DARK_MUTED, size=10),
                        leading=ft.Icons.TUNE_OUTLINED, expanded=False,
                        controls=[ft.ResponsiveRow([
                            ft.Container(size_field, col={"xs": 12, "md": 4}),
                            ft.Container(standard_field, col={"xs": 12, "md": 4}),
                            ft.Container(brand_field, col={"xs": 12, "md": 4}),
                            ft.Container(model_field, col={"xs": 12, "md": 4}),
                            ft.Container(condition_field, col={"xs": 12, "md": 4}),
                            ft.Container(expiry_field, col={"xs": 12, "md": 4}),
                        ], spacing=10, run_spacing=10)],
                    ),
                    ft.Row([cancel_edit_button, save_item_button], spacing=10, alignment=ft.MainAxisAlignment.END),
                ]),
                _panel("Catalogue", [search_field, catalog_area]),
            ], spacing=12)

        elif sub == "mouvements":
            content = _panel("Mouvements de stock", [
                ft.Row([
                    movement_item_field, movement_type_field, movement_quantity_field,
                    movement_motif_field, movement_reference_field,
                    ft.ElevatedButton("Enregistrer", on_click=save_movement),
                ], wrap=True, spacing=10),
                ft.Row([
                    movement_filter_item, movement_filter_type, movement_filter_employee, movement_filter_date,
                    ft.OutlinedButton("Appliquer", icon=ft.Icons.FILTER_ALT_OUTLINED, on_click=lambda e: refresh()),
                ], wrap=True, spacing=10),
                movement_area,
            ])

        elif sub == "inspections":
            content = _panel("Inspections EPI", [
                ft.Row([
                    inspection_item_field, inspection_status_field, inspection_date_field,
                    inspection_next_field, inspection_inspector_field, inspection_observation_field,
                    ft.ElevatedButton("Enregistrer inspection", on_click=save_inspection),
                ], wrap=True, spacing=10),
                inspection_area,
            ])

        elif sub == "conformite":
            content = ft.Column([
                _panel("Conformité EPI par employé", [compliance_summary_area]),
                _panel("Règles obligatoires par fonction", [
                    ft.Row([
                        requirement_function_field, requirement_type_field,
                        requirement_quantity_field, requirement_mandatory_field,
                        ft.ElevatedButton("Enregistrer", on_click=save_requirement),
                    ], wrap=True, spacing=10),
                    requirement_area,
                    compliance_area,
                ]),
                _panel("Exports professionnels", [
                    ft.Text("Exports avec légendes couleur et zones de signature.", color=DARK_MUTED, size=10),
                    ft.Row([
                        ft.ElevatedButton("Inventaire EPI", icon=ft.Icons.INVENTORY_2_OUTLINED, on_click=export_inventory),
                        ft.OutlinedButton("Employés dotés", icon=ft.Icons.GROUPS_OUTLINED, on_click=export_equipped_employees),
                        ft.OutlinedButton("Conformité", icon=ft.Icons.FACT_CHECK_OUTLINED, on_click=export_compliance),
                        ft.OutlinedButton("Inspections", icon=ft.Icons.EVENT_REPEAT_OUTLINED, on_click=export_inspections),
                    ], spacing=10, wrap=True),
                ]),
            ], spacing=12)

        elif sub == "dotation":
            content = _panel("Dotation EPI — Multi-bénéficiaires", [
                # Étape 1 — Bénéficiaires
                ft.Container(
                    bgcolor=FIELD, border=ft.border.all(1, DARK_BORDER), border_radius=8, padding=12,
                    content=ft.Column([
                        _step_header(PRIMARY, "ÉTAPE 1 — Sélection des bénéficiaires"),
                        ft.Row([
                            emp_search_field,
                            ft.ElevatedButton("Tout sélectionner", icon=ft.Icons.CHECK_BOX_OUTLINED, on_click=_select_all_employees, bgcolor="#142B45", color=PRIMARY),
                            ft.OutlinedButton("Tout désélectionner", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=_deselect_all_employees,
                                style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: DARK_MUTED}, side=ft.BorderSide(1, DARK_BORDER))),
                        ], spacing=8, wrap=True),
                        ft.Row([
                            ft.Icon(ft.Icons.GROUP_WORK_OUTLINED, color=DARK_MUTED, size=16),
                            ft.Text("Groupe :", color=DARK_MUTED, size=10),
                            group_func_dd, group_site_dd,
                            ft.ElevatedButton("Sélectionner ce groupe", icon=ft.Icons.GROUP_ADD_OUTLINED, on_click=_select_employees_by_group, bgcolor="#142B45", color=SUCCESS),
                        ], spacing=8, wrap=True, vertical_alignment=ft.CrossAxisAlignment.END),
                        ft.Container(
                            content=employee_list_area, bgcolor=BG,
                            border=ft.border.all(1, DARK_BORDER), border_radius=6,
                            padding=8, height=200, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        ),
                        selected_count_text,
                    ], spacing=8),
                ),
                # Étape 2 — Panier EPI
                ft.Container(
                    bgcolor=FIELD, border=ft.border.all(1, DARK_BORDER), border_radius=8, padding=12,
                    content=ft.Column([
                        _step_header(SUCCESS, "ÉTAPE 2 — Composition du panier EPI"),
                        ft.Row([
                            assignment_item_field, assignment_quantity_field,
                            ft.ElevatedButton("Ajouter au panier", icon=ft.Icons.ADD_SHOPPING_CART_OUTLINED, on_click=add_assignment_to_basket, bgcolor=PRIMARY, color="#FFFFFF"),
                            ft.OutlinedButton("Dotation automatique", icon=ft.Icons.AUTO_FIX_HIGH_OUTLINED, on_click=assign_all_required,
                                style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: SUCCESS}, side=ft.BorderSide(1, SUCCESS))),
                        ], spacing=10, wrap=True, vertical_alignment=ft.CrossAxisAlignment.END),
                        assignment_basket_area,
                    ], spacing=8),
                ),
                # Étape 3 — Validation
                ft.Container(
                    bgcolor=FIELD, border=ft.border.all(1, DARK_BORDER), border_radius=8, padding=12,
                    content=ft.Column([
                        _step_header(WARNING, "ÉTAPE 3 — Validation et émission"),
                        ft.Row([assignment_date_field, issued_by_field, assignment_observation_field], spacing=10, wrap=True, vertical_alignment=ft.CrossAxisAlignment.END),
                        ft.Row([
                            ft.ElevatedButton("Attribuer à tous les sélectionnés", icon=ft.Icons.ASSIGNMENT_IND_OUTLINED, bgcolor=SUCCESS, color="#FFFFFF", on_click=_do_batch_assign),
                            ft.OutlinedButton("Générer fiche PDF", icon=ft.Icons.PICTURE_AS_PDF_OUTLINED, on_click=_generate_fiche,
                                style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: WARNING}, side=ft.BorderSide(1, WARNING))),
                            ft.ElevatedButton("Attribuer + Fiche PDF", icon=ft.Icons.DONE_ALL_OUTLINED, bgcolor=PRIMARY, color="#FFFFFF", on_click=_do_batch_assign_and_fiche),
                        ], spacing=10, wrap=True),
                        status,
                    ], spacing=8),
                ),
                # Liste des employés dotés
                ft.Divider(color=DARK_BORDER),
                ft.Row([
                    ft.Text("Liste des employés dotés", color=DARK_TEXT, size=14, weight=ft.FontWeight.BOLD, expand=True),
                    ft.OutlinedButton("Actualiser", icon=ft.Icons.REFRESH, on_click=render_dotation_list,
                        style=ft.ButtonStyle(color={ft.ControlState.DEFAULT: DARK_MUTED}, side=ft.BorderSide(1, DARK_BORDER))),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                dotation_list_area,
            ])

        else:
            content = ft.Text("Sélectionnez un sous-onglet.", color=DARK_MUTED, size=12)

        tab3_col.controls = [sub_nav, content]
        try:
            tab3_col.update()
        except RuntimeError:
            pass

    def _switch_gestion(name: str) -> None:
        state["gestion_tab"] = name
        render_tab3()
        _update()

    # ── Tab switching ──────────────────────────────────────────────────────────

    def render_active_tab() -> None:
        tab = state["tab"]
        if tab == "overview":
            render_tab1()
        elif tab == "employees":
            render_tab2()
        elif tab == "gestion":
            render_tab3()

    def switch_tab(name: str) -> None:
        state["tab"] = name
        for n, btn in tab_buttons.items():
            sel = n == name
            btn.style = ft.ButtonStyle(
                color="#FFFFFF" if sel else "#C7D4E3",
                bgcolor=PRIMARY if sel else FIELD,
                shape=ft.RoundedRectangleBorder(radius=8),
            )
        render_active_tab()
        _update()

    def _make_tab_btn(name: str, label: str, icon: str) -> ft.TextButton:
        btn = ft.TextButton(
            label, icon=icon,
            on_click=lambda e, n=name: switch_tab(n),
            style=ft.ButtonStyle(
                color="#FFFFFF" if state["tab"] == name else "#C7D4E3",
                bgcolor=PRIMARY if state["tab"] == name else FIELD,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )
        tab_buttons[name] = btn
        return btn

    btn_overview = _make_tab_btn("overview", "Vue d'ensemble", ft.Icons.DASHBOARD_OUTLINED)
    btn_employees = _make_tab_btn("employees", "Employés & Dotations", ft.Icons.BADGE_OUTLINED)
    btn_gestion = _make_tab_btn("gestion", "Gestion EPI", ft.Icons.HEALTH_AND_SAFETY_OUTLINED)

    # ── Root layout ────────────────────────────────────────────────────────────

    tab_bar = ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, DARK_BORDER),
        border_radius=8,
        padding=8,
        content=ft.Row([btn_overview, btn_employees, btn_gestion], spacing=6, wrap=True),
    )

    root = ft.Container(
        bgcolor=BG,
        expand=True,
        content=ft.Column(
            controls=[
                _ppe_header(),
                tab_bar,
                ft.Container(
                    content=ft.Stack([
                        ft.Container(content=tab1_col, visible=True),
                        ft.Container(content=tab2_col, visible=False),
                        ft.Container(content=tab3_col, visible=False),
                    ]),
                    expand=True,
                ),
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    # Simpler: use a Column with a single visible tab_content area
    # Replace Stack with a direct content area swapped by switch_tab
    tab_content_area = ft.Container(expand=True)

    def switch_tab(name: str) -> None:  # noqa: F811 — intentional override
        state["tab"] = name
        for n, btn in tab_buttons.items():
            sel = n == name
            btn.style = ft.ButtonStyle(
                color="#FFFFFF" if sel else "#C7D4E3",
                bgcolor=PRIMARY if sel else FIELD,
                shape=ft.RoundedRectangleBorder(radius=8),
            )
        if name == "overview":
            render_tab1()
            tab_content_area.content = tab1_col
        elif name == "employees":
            render_tab2()
            tab_content_area.content = tab2_col
        elif name == "gestion":
            render_tab3()
            tab_content_area.content = tab3_col
        _update()

    # Re-wire tab buttons with final switch_tab
    for _n, _btn in tab_buttons.items():
        _btn.on_click = lambda e, n=_n: switch_tab(n)

    def render_active_tab() -> None:  # noqa: F811
        tab = state["tab"]
        if tab == "overview":
            render_tab1()
        elif tab == "employees":
            render_tab2()
        elif tab == "gestion":
            render_tab3()

    root = ft.Container(
        bgcolor=BG,
        expand=True,
        content=ft.Column(
            controls=[
                _ppe_header(),
                ft.Container(
                    bgcolor=CARD,
                    border=ft.border.all(1, DARK_BORDER),
                    border_radius=8,
                    padding=8,
                    content=ft.Row([btn_overview, btn_employees, btn_gestion], spacing=6, wrap=True),
                ),
                tab_content_area,
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    # Initialise
    tab_content_area.content = tab1_col
    refresh()
    render_assignment_basket()
    save_item_button.on_click = save_item
    cancel_edit_button.on_click = lambda e: (reset_item_form(), refresh())
    return root


# ── Module-level helpers ───────────────────────────────────────────────────────

def _info_chip(icon: str, label: str, value: str, color: str = DARK_MUTED) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, DARK_BORDER),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        content=ft.Row([
            ft.Icon(icon, color=color, size=14),
            ft.Column([
                ft.Text(label, size=9, color=DARK_MUTED),
                ft.Text(value, size=13, color=color if color != DARK_MUTED else DARK_TEXT, weight=ft.FontWeight.W_600),
            ], spacing=1),
        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )


def _summary_chip(label: str, value: Any, color: str, icon: str) -> ft.Control:
    return ft.Container(
        col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
        bgcolor=CARD,
        border=ft.border.all(1, DARK_BORDER),
        border_radius=8,
        padding=12,
        content=ft.Row([
            ft.Container(
                width=40, height=40, bgcolor=color, border_radius=8,
                alignment=ft.Alignment(0, 0),
                content=ft.Icon(icon, color="#FFFFFF", size=21),
            ),
            ft.Column([
                ft.Text(label, color=DARK_MUTED, size=10),
                ft.Text(str(value), color=DARK_TEXT, size=20, weight=ft.FontWeight.BOLD),
            ], spacing=0),
        ], spacing=9),
    )


def _panel(title: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, DARK_BORDER),
        border_radius=8,
        padding=14,
        content=ft.Column(
            controls=[ft.Text(title, color=DARK_TEXT, size=14, weight=ft.FontWeight.BOLD), *controls],
            spacing=12,
        ),
    )


def _info_line(label: str, value: Any, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, DARK_BORDER),
        border_radius=8,
        padding=9,
        content=ft.Row(
            controls=[
                ft.Text(label, color=DARK_MUTED, size=10),
                ft.Text(str(value), color=color, size=11, weight=ft.FontWeight.BOLD),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
    )


def _required_ppe_row(row: dict[str, Any]) -> ft.Control:
    status = str(row.get("statut") or "")
    labels = {
        "deja_attribue": "Déjà attribué", "disponible": "Disponible",
        "manquant": "Manquant", "stock_insuffisant": "Stock insuffisant",
    }
    colors = {
        "deja_attribue": SUCCESS, "disponible": PRIMARY,
        "manquant": DANGER, "stock_insuffisant": WARNING,
    }
    color = colors.get(status, DARK_MUTED)
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, color),
        border_radius=8,
        padding=10,
        content=ft.Row([
            ft.Icon(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, color=color, size=18),
            ft.Column([
                ft.Text(str(row.get("type_epi") or "-"), color=DARK_TEXT, weight=ft.FontWeight.BOLD, size=11),
                ft.Text(
                    f"Requis {row.get('requis', 0)} | Attribué {row.get('attribue', 0)} | Stock {row.get('stock_disponible', 0)}",
                    color=DARK_MUTED, size=9,
                ),
            ], spacing=1, expand=True),
            _status_badge(labels.get(status, status or "-"), color),
        ], spacing=9),
    )


def _alert_row(row: dict[str, Any]) -> ft.Control:
    level = str(row.get("niveau") or "moyen")
    color = DANGER if level == "critique" else WARNING if level in {"haut", "attention"} else PRIMARY
    category = str(row.get("categorie") or "alerte").replace("_", " ").title()
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, color),
        border_radius=8,
        padding=10,
        content=ft.Row([
            ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED, color=color, size=19),
            ft.Column([
                ft.Text(category, color=color, size=10, weight=ft.FontWeight.BOLD),
                ft.Text(str(row.get("message") or "-"), color=DARK_TEXT, size=10),
            ], spacing=2, expand=True),
            _status_badge(str(row.get("statut") or "ouverte").title(), color),
        ], spacing=8),
    )


def _compliance_employee_row(row: dict[str, Any]) -> ft.Control:
    percentage = int(row.get("pourcentage") or 0)
    status = str(row.get("statut") or "manquant")
    color = SUCCESS if status == "conforme" else DANGER
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, DARK_BORDER),
        border_radius=8,
        padding=10,
        content=ft.Row([
            ft.Column([
                ft.Text(
                    f"{row.get('nom') or '-'} {row.get('prenom') or ''}".strip(),
                    color=DARK_TEXT, weight=ft.FontWeight.BOLD, size=11,
                ),
                ft.Text(f"{row.get('fonction') or '-'} | {row.get('site') or '-'}", color=DARK_MUTED, size=9),
                ft.Text(f"Manquants: {row.get('epi_manquants') or '-'}", color=color, size=9),
            ], spacing=1, expand=True),
            ft.Column([
                ft.Text(f"{row.get('recus', 0)}/{row.get('requis', 0)} reçus", color=DARK_MUTED, size=9),
                _status_badge(f"{percentage}% - {status.title()}", color),
            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.END),
        ], spacing=8),
    )


def _status_badge(label: str, color: str) -> ft.Control:
    return ft.Container(
        bgcolor=FIELD,
        border=ft.border.all(1, color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(label, size=11, color=color, weight=ft.FontWeight.BOLD),
    )


def _recommendation_card(title: str, description: str, icon: str) -> ft.Control:
    return ft.Container(
        col={"sm": 12, "md": 4},
        bgcolor=FIELD,
        border=ft.border.all(1, DARK_BORDER),
        border_radius=8,
        padding=12,
        content=ft.Row([
            ft.Icon(icon, color=PRIMARY, size=20),
            ft.Column([
                ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=DARK_TEXT),
                ft.Text(description, size=11, color=DARK_MUTED),
            ], spacing=3, expand=True),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
    )


def _recommendations_row() -> ft.Control:
    return ft.ResponsiveRow(
        controls=[
            _recommendation_card("Dotation par fonction", "Prépare et attribue automatiquement les EPI obligatoires disponibles.", ft.Icons.AUTO_FIX_HIGH_OUTLINED),
            _recommendation_card("Conformité employés", "Identifie immédiatement les dotations manquantes et les blocages.", ft.Icons.FACT_CHECK_OUTLINED),
            _recommendation_card("Inspections et alertes", "Actualise les contrôles en retard, expirations et stocks critiques.", ft.Icons.WARNING_AMBER_OUTLINED),
        ],
        spacing=10,
        run_spacing=10,
    )


def _ppe_header() -> ft.Control:
    return ft.Container(
        bgcolor=CARD,
        border=ft.border.all(1, DARK_BORDER),
        border_radius=8,
        padding=14,
        content=ft.Row([
            ft.Container(
                width=44, height=44, bgcolor=PRIMARY, border_radius=8,
                alignment=ft.Alignment(0, 0),
                content=ft.Icon(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, color="#FFFFFF", size=24),
            ),
            ft.Column([
                ft.Text("Gestion des EPI", color=DARK_TEXT, size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Catalogue, dotations employés, inspections et conformité.", color=DARK_MUTED, size=11),
            ], spacing=2),
        ], spacing=12),
    )
