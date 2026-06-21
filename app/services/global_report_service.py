from __future__ import annotations
import os
import platform
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Any


def _reports_dir() -> Path:
    p = Path("exports/rapports")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _unique_path(filename: str) -> Path:
    base = _reports_dir() / filename
    if not base.exists():
        return base
    stem, suffix = base.stem, base.suffix
    i = 1
    while True:
        candidate = _reports_dir() / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def open_report_file(path: Path) -> None:
    if platform.system() == "Windows":
        os.startfile(str(path))
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def export_monthly_qhse_report(year: int | None = None, month: int | None = None) -> Path:
    today = date.today()
    y = year or today.year
    m = month or today.month
    month_str = f"{y:04d}-{m:02d}"
    month_label = datetime(y, m, 1).strftime("%B %Y")
    path = _unique_path(f"Rapport_QHSE_{month_str}.pdf")
    try:
        _write_monthly_pdf(path, y, m, month_label, month_str)
    except Exception as exc:
        _write_report_fallback(path, month_label, str(exc))
    return path


def _write_monthly_pdf(
    path: Path, year: int, month: int, month_label: str, month_str: str
) -> None:
    from reportlab.lib import colors
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        BaseDocTemplate, Frame, PageTemplate,
        Paragraph, Spacer, Table, TableStyle, PageBreak,
    )

    NAVY       = HexColor("#0D1B2A")
    NAVY_LIGHT = HexColor("#1E3A5F")
    WHITE      = colors.white
    PRIMARY    = HexColor("#3B82F6")
    SUCCESS    = HexColor("#10B981")
    WARNING    = HexColor("#F59E0B")
    DANGER     = HexColor("#EF4444")
    MUTED      = HexColor("#9DB0C5")
    LIGHT_BG   = HexColor("#F0F4F8")

    W, H = A4
    styles = getSampleStyleSheet()
    normal = ParagraphStyle("n", parent=styles["Normal"], fontSize=9, leading=13, textColor=NAVY)
    bold   = ParagraphStyle("b", parent=styles["Normal"], fontSize=10, leading=14, fontName="Helvetica-Bold", textColor=NAVY)
    title_s= ParagraphStyle("t", parent=styles["Normal"], fontSize=16, leading=20, fontName="Helvetica-Bold", textColor=WHITE)
    sub_s  = ParagraphStyle("s", parent=styles["Normal"], fontSize=11, leading=15, fontName="Helvetica-Bold", textColor=WHITE)
    section_s = ParagraphStyle("sec", parent=styles["Normal"], fontSize=13, leading=17, fontName="Helvetica-Bold", textColor=NAVY)
    MUTED_S = ParagraphStyle("m", parent=styles["Normal"], fontSize=8, leading=11, textColor=MUTED)

    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    def _header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, H - 18*mm, W, 18*mm, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(15*mm, H - 12*mm, "OREZONE QHSE")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(W - 15*mm, H - 12*mm, f"Rapport confidentiel | Page {doc.page}")
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, W, 8*mm, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(15*mm, 3*mm, f"OREZONE QHSE — Rapport mensuel {month_label} — Généré le {generated_at}")
        canvas.restoreState()

    frame = Frame(15*mm, 12*mm, W - 30*mm, H - 32*mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc = BaseDocTemplate(str(path), pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=20*mm, bottomMargin=14*mm)
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_header_footer)])

    def _section_title(text: str) -> list:
        return [
            Spacer(1, 6*mm),
            Table([[Paragraph(text, section_s)]], colWidths=[W - 30*mm],
                  style=TableStyle([
                      ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                      ("LEFTPADDING", (0, 0), (-1, -1), 8),
                      ("TOPPADDING", (0, 0), (-1, -1), 5),
                      ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                      ("LINEBELOW", (0, 0), (-1, -1), 1.5, PRIMARY),
                  ])),
            Spacer(1, 3*mm),
        ]

    def _kpi_table(rows: list[tuple[str, str, Any]]) -> Table:
        data = [[Paragraph(k, bold), Paragraph(str(v), normal), Paragraph(n, MUTED_S)] for k, v, n in rows]
        t = Table(data, colWidths=[55*mm, 30*mm, W - 30*mm - 55*mm - 30*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#D1D9E0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return t

    def _data_table(headers: list[str], rows: list[list[str]], col_widths: list[float]) -> Table:
        header_row = [Paragraph(h, bold) for h in headers]
        data_rows = [[Paragraph(str(c), normal) for c in row] for row in rows]
        t = Table([header_row] + data_rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#D1D9E0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    story = []

    # ── Cover ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20*mm))
    story.append(Table(
        [[Paragraph("RAPPORT QHSE MENSUEL", title_s)],
         [Paragraph(f"OREZONE QHSE — {month_label}", sub_s)],
         [Paragraph(f"Généré le {generated_at} | Document confidentiel", MUTED_S)]],
        colWidths=[W - 30*mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 1), NAVY),
            ("BACKGROUND", (0, 2), (-1, 2), NAVY_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ]),
    ))
    story.append(Spacer(1, 10*mm))

    # Collect data (all try/except)
    acc_summary: dict = {}
    acc_kpis: dict = {}
    accidents_month: list = []
    risk_list: list = []
    ppe_summary: dict = {}
    expiring_epi: list = []
    permit_summary: dict = {}
    permits_month: list = []

    try:
        from app.services.accident_service import get_accident_summary, compute_kpis, list_accidents
        acc_summary = get_accident_summary()
        acc_kpis = compute_kpis()
        accidents_month = [a for a in list_accidents() if str(a.get("date_evenement", "")).startswith(month_str)]
    except Exception:
        pass

    try:
        from app.services.risk_service import list_risks
        risk_list = list_risks()
    except Exception:
        pass

    try:
        from app.services.ppe_service import get_ppe_summary, get_expiring_assigned_ppe
        ppe_summary = get_ppe_summary()
        expiring_epi = get_expiring_assigned_ppe(60)
    except Exception:
        pass

    try:
        from app.services.permit_service import get_permit_summary, list_permits
        permit_summary = get_permit_summary()
        permits_month = [p for p in list_permits() if str(p.get("date_emission", "")).startswith(month_str)]
    except Exception:
        pass

    # ── Section 1 — Résumé exécutif ───────────────────────────────────────
    story.extend(_section_title("1. RÉSUMÉ EXÉCUTIF"))
    kpi_rows = [
        ("Accidents ce mois", len(accidents_month), "dont AT avec arrêt"),
        ("Accidents ouverts total", acc_summary.get("ouverts", 0), "en cours d'investigation"),
        ("Taux de fréquence (TF)", acc_kpis.get("tf", 0), "/million heures"),
        ("Taux de gravité (TG)", acc_kpis.get("tg", 0), "/millier heures"),
        ("Risques actifs", len([r for r in risk_list if r.get("status") != "clos"]), "statut non clos"),
        ("Conformité EPI", f"{ppe_summary.get('compliance_rate', 0)}%", "global"),
        ("Permis actifs", permit_summary.get("actifs", 0), "en cours"),
        ("Permis en attente validation", permit_summary.get("en_attente", 0), "à traiter"),
    ]
    story.append(_kpi_table(kpi_rows))

    story.append(PageBreak())

    # ── Section 2 — Accidents ─────────────────────────────────────────────
    story.extend(_section_title(f"2. ACCIDENTS & INCIDENTS — {month_label}"))
    if accidents_month:
        story.append(_data_table(
            ["N°", "Date", "Type", "Lieu", "Gravité", "Statut"],
            [
                [
                    a.get("numero", "—"), a.get("date_evenement", "—"),
                    a.get("type_evenement", "—").replace("_", " ").title(),
                    a.get("lieu", "—"), a.get("gravite", "—").title(),
                    a.get("statut", "—").title(),
                ]
                for a in accidents_month
            ],
            [20*mm, 22*mm, 35*mm, 35*mm, 22*mm, 22*mm],
        ))
    else:
        story.append(Paragraph(f"Aucun accident enregistré pour {month_label}.", normal))

    # ── Section 3 — Permis ────────────────────────────────────────────────
    story.extend(_section_title(f"3. PERMIS DE TRAVAIL — {month_label}"))
    if permits_month:
        story.append(_data_table(
            ["N°", "Type", "Titre", "Lieu", "Du", "Au", "Statut"],
            [
                [
                    p.get("numero", "—"),
                    p.get("type_permis", "—").replace("_", " ").title(),
                    str(p.get("titre", "—"))[:30],
                    p.get("lieu", "—"),
                    p.get("date_debut", "—"), p.get("date_fin", "—"),
                    p.get("statut", "—").title(),
                ]
                for p in permits_month
            ],
            [22*mm, 22*mm, 40*mm, 25*mm, 18*mm, 18*mm, 18*mm],
        ))
    else:
        story.append(Paragraph(f"Aucun permis émis pour {month_label}.", normal))

    story.append(PageBreak())

    # ── Section 4 — EPI ───────────────────────────────────────────────────
    story.extend(_section_title("4. GESTION DES EPI"))
    ppe_kpis = [
        ("Total EPI catalogue", ppe_summary.get("items", 0), "références"),
        ("Stock total", ppe_summary.get("stock_total", 0), "unités"),
        ("EPI affectés", ppe_summary.get("assigned", 0), "en service"),
        ("Stock bas / critiques", ppe_summary.get("low_stock", 0), "en dessous du seuil"),
        ("EPI expirés", ppe_summary.get("expired", 0), "à remplacer"),
        ("Taux de conformité", f"{ppe_summary.get('compliance_rate', 0)}%", "global"),
    ]
    story.append(_kpi_table(ppe_kpis))
    if expiring_epi:
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph("EPI expirant dans les 60 prochains jours :", bold))
        story.append(Spacer(1, 2*mm))
        story.append(_data_table(
            ["Employé", "Type EPI", "Désignation", "Date expiration", "J restants"],
            [
                [
                    f"{e.get('nom', '')} {e.get('prenom', '')}".strip(),
                    e.get("type_epi", "—"), e.get("epi_nom", "—"),
                    e.get("date_expiration", "—"), str(e.get("jours_restants", "?")),
                ]
                for e in expiring_epi[:20]
            ],
            [45*mm, 30*mm, 35*mm, 28*mm, 19*mm],
        ))

    # ── Section 5 — Risques ───────────────────────────────────────────────
    story.extend(_section_title("5. REGISTRE DES RISQUES"))
    active_risks = [r for r in risk_list if r.get("status") != "clos"]
    if active_risks:
        from collections import Counter
        level_dist = Counter(r.get("risk_level", "moyen") for r in active_risks)
        story.append(_kpi_table([
            ("Critique (Score ≥15)", level_dist.get("critique", 0), "action immédiate"),
            ("Élevé (Score 10-14)",  level_dist.get("eleve", 0),    "surveillance renforcée"),
            ("Moyen (Score 5-9)",    level_dist.get("moyen", 0),    "à planifier"),
            ("Faible (Score 1-4)",   level_dist.get("faible", 0),   "acceptable"),
        ]))
        story.append(Spacer(1, 4*mm))
        story.append(_data_table(
            ["Titre", "Zone", "Score", "Niveau", "Statut", "Responsable"],
            [
                [
                    str(r.get("title") or r.get("activity", "—"))[:35],
                    r.get("location") or r.get("zone", "—"),
                    r.get("risk_score", "—"),
                    r.get("risk_level", "—").title(),
                    r.get("status", "—").title(),
                    r.get("owner", "—"),
                ]
                for r in active_risks[:20]
            ],
            [45*mm, 28*mm, 15*mm, 20*mm, 18*mm, 31*mm],
        ))
    else:
        story.append(Paragraph("Aucun risque actif.", normal))

    doc.build(story)


def export_accident_report(accident_id: int) -> Path:
    path = _unique_path(f"Rapport_Accident_{accident_id}.pdf")
    try:
        _write_accident_pdf(path, accident_id)
    except Exception as exc:
        _write_report_fallback(path, f"Accident #{accident_id}", str(exc))
    return path


def _write_accident_pdf(path: Path, accident_id: int) -> None:
    from reportlab.lib import colors
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    )

    from app.services.accident_service import get_accident, list_causes, list_actions
    accident = get_accident(accident_id)
    if not accident:
        raise ValueError(f"Accident #{accident_id} introuvable.")
    causes = list_causes(accident_id)
    actions = list_actions(accident_id)

    NAVY    = HexColor("#0D1B2A")
    WHITE   = colors.white
    LIGHT   = HexColor("#F0F4F8")
    DANGER  = HexColor("#EF4444")
    WARNING = HexColor("#F59E0B")
    SUCCESS = HexColor("#10B981")

    GRAVITE_COLORS = {
        "fatal": HexColor("#7C3AED"), "grave": DANGER,
        "majeur": WARNING, "mineur": HexColor("#F97316"), "benin": SUCCESS,
    }
    grav_clr = GRAVITE_COLORS.get(accident.get("gravite", "benin"), WARNING)

    W, H = A4
    styles = getSampleStyleSheet()
    normal = ParagraphStyle("n", fontSize=9, leading=13, textColor=NAVY)
    bold   = ParagraphStyle("b", fontSize=9, leading=13, fontName="Helvetica-Bold", textColor=NAVY)
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    def _label_value(label: str, value: Any) -> Table:
        t = Table(
            [[Paragraph(label, bold), Paragraph(str(value or "—"), normal)]],
            colWidths=[45*mm, W - 40*mm - 45*mm],
        )
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), LIGHT),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#D1D9E0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return t

    def _section(title: str) -> Paragraph:
        return Paragraph(
            f"<b>{title}</b>",
            ParagraphStyle("sec", fontSize=10, fontName="Helvetica-Bold", textColor=NAVY,
                           backColor=LIGHT, leftPadding=6, topPadding=4, bottomPadding=4,
                           borderPadding=4),
        )

    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    story = []

    # Header
    emp_name = f"{accident.get('employe_nom', '')} {accident.get('employe_prenom', '')}".strip()
    story.append(Table(
        [[Paragraph("RAPPORT D'ACCIDENT / INCIDENT", ParagraphStyle(
            "h", fontSize=14, fontName="Helvetica-Bold", textColor=WHITE))],
         [Paragraph(f"Réf: {accident.get('numero', '?')} | {accident.get('date_evenement', '?')} | {generated_at}", ParagraphStyle(
            "sh", fontSize=8, textColor=HexColor("#9DB0C5")))]],
        colWidths=[W - 40*mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("BACKGROUND", (0, 1), (-1, 1), HexColor("#1E3A5F")),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]),
    ))
    story.append(Spacer(1, 4*mm))

    # Gravité badge
    story.append(Table(
        [[Paragraph(f"GRAVITÉ : {accident.get('gravite', '?').upper()}", ParagraphStyle(
            "grav", fontSize=11, fontName="Helvetica-Bold", textColor=WHITE))]],
        colWidths=[W - 40*mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), grav_clr),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]),
    ))
    story.append(Spacer(1, 4*mm))

    # Section 1: Identification
    story.append(_section("1. IDENTIFICATION"))
    story.append(Spacer(1, 2*mm))
    for label, field in [
        ("Type", accident.get("type_evenement", "").replace("_", " ").title()),
        ("Date / Heure", f"{accident.get('date_evenement', '—')} {accident.get('heure_evenement', '')}".strip()),
        ("Lieu", accident.get("lieu")), ("Zone", accident.get("zone")),
        ("Employé concerné", emp_name or "—"),
        ("Tiers impliqué", accident.get("tiers_implique")),
        ("Jours d'arrêt", accident.get("jours_arret", 0)),
        ("Statut", accident.get("statut", "").title()),
    ]:
        story.append(_label_value(label, field))
    story.append(Spacer(1, 4*mm))

    # Section 2: Description
    story.append(_section("2. DESCRIPTION DE L'ÉVÉNEMENT"))
    story.append(Spacer(1, 2*mm))
    desc_text = str(accident.get("description") or "Non renseigné")
    story.append(Table(
        [[Paragraph(desc_text, normal)]],
        colWidths=[W - 40*mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#D1D9E0")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]),
    ))
    story.append(Spacer(1, 4*mm))

    # Section 3: Causes
    story.append(_section("3. ANALYSE DES CAUSES"))
    story.append(Spacer(1, 2*mm))
    if causes:
        cause_type_labels = {"immediate": "Immédiate", "racine": "Racine", "systemique": "Systémique"}
        for c in causes:
            ct = cause_type_labels.get(c.get("type_cause", ""), c.get("type_cause", ""))
            story.append(_label_value(ct, c.get("description", "—")))
    else:
        story.append(Paragraph("Aucune cause renseignée.", normal))
    story.append(Spacer(1, 4*mm))

    # Section 4: Actions
    story.append(_section("4. ACTIONS CORRECTIVES"))
    story.append(Spacer(1, 2*mm))
    if actions:
        story.append(Table(
            [[Paragraph("Description", bold), Paragraph("Responsable", bold),
              Paragraph("Échéance", bold), Paragraph("Statut", bold)]] +
            [[
                Paragraph(str(a.get("description", "—")), normal),
                Paragraph(str(a.get("responsable", "—")), normal),
                Paragraph(str(a.get("date_echeance", "—")), normal),
                Paragraph(str(a.get("statut", "—")).title(), normal),
            ] for a in actions],
            colWidths=[70*mm, 40*mm, 28*mm, 22*mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#D1D9E0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]),
        ))
    else:
        story.append(Paragraph("Aucune action corrective renseignée.", normal))
    story.append(Spacer(1, 8*mm))

    # Signature boxes
    sig_style = ParagraphStyle("sig", fontSize=8, leading=12, textColor=NAVY, alignment=1)
    sig_data = [
        [Paragraph("Déclaré par", sig_style),
         Paragraph("Responsable HSE", sig_style),
         Paragraph("Directeur de site", sig_style)],
        [Paragraph("\n\n\n\n_____________________", sig_style),
         Paragraph("\n\n\n\n_____________________", sig_style),
         Paragraph("\n\n\n\n_____________________", sig_style)],
        [Paragraph("Nom & Date", sig_style)] * 3,
    ]
    story.append(Table(sig_data, colWidths=[(W - 40*mm) / 3] * 3,
                       style=TableStyle([
                           ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#D1D9E0")),
                           ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                           ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                       ])))

    doc.build(story)


def _write_report_fallback(path: Path, label: str, error: str = "") -> None:
    txt_path = path.with_suffix(".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"OREZONE QHSE — {label}\n")
        f.write(f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
        if error:
            f.write(f"Erreur génération PDF : {error}\n")
