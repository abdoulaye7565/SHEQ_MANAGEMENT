from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import EXPORTS_DIR
from app.services.risk_service import get_risk_heatmap, get_risk_summary, list_controls, list_risks
from app.services.xlsx_service import write_styled_xlsx

_LEVEL_STYLE = {
    "critique": "danger",
    "eleve": "permission",
    "moyen": "soon",
    "faible": "done",
}
_LEVEL_LABEL = {
    "critique": "CRITIQUE",
    "eleve": "ÉLÉVÉ",
    "moyen": "MOYEN",
    "faible": "FAIBLE",
}
_STATUS_LABEL = {
    "ouvert": "Ouvert",
    "en_cours": "En cours",
    "clos": "Clos",
}


def _unique_path(filename: str) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORTS_DIR / filename
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for i in range(1, 999):
        candidate = EXPORTS_DIR / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
    return path


def export_risk_register_xlsx(
    status: str | None = None,
    level: str | None = None,
    hazard_type: str | None = None,
) -> Path:
    risks = list_risks(status=status, level=level, hazard_type=hazard_type)
    summary = get_risk_summary()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    headers = [
        "N°", "Titre du Risque", "Activité", "Zone", "Type de Danger",
        "Personnes Exposées", "P", "G", "Score Initial", "Niveau Initial",
        "Mesures Existantes",
        "P Résiduel", "G Résiduel", "Score Résiduel", "Niveau Résiduel",
        "Statut", "Responsable", "Date Révision",
    ]

    summary_row1 = [
        "Total Risques", summary.get("total", 0),
        "Critiques", summary.get("critique", 0),
        "Élevés", summary.get("eleve", 0),
        "Moyens", summary.get("moyen", 0),
        "Faibles", summary.get("faible", 0),
    ]
    summary_row2: list[Any] = []
    summary_row3 = [
        "Ouverts", summary.get("ouvert", 0),
        "En cours", summary.get("en_cours", 0),
        "Clos", summary.get("clos", 0),
        "Généré le", generated_at,
    ]
    summary_row4: list[Any] = []

    data_rows: list[list[Any]] = []
    data_styles: list[list[str | None]] = []

    for risk in risks:
        lvl = str(risk.get("risk_level") or "faible")
        res_lvl = str(risk.get("residual_level") or "faible")
        style_key = _LEVEL_STYLE.get(lvl, "soon")
        res_style = _LEVEL_STYLE.get(res_lvl, "soon")
        row: list[Any] = [
            risk.get("id", ""),
            str(risk.get("title") or ""),
            str(risk.get("activity") or ""),
            str(risk.get("zone") or ""),
            str(risk.get("hazard_type") or ""),
            str(risk.get("affected_people") or ""),
            risk.get("probability", ""),
            risk.get("severity", ""),
            risk.get("risk_score", ""),
            _LEVEL_LABEL.get(lvl, lvl.upper()),
            str(risk.get("existing_controls") or ""),
            risk.get("residual_probability", ""),
            risk.get("residual_severity", ""),
            risk.get("residual_score", ""),
            _LEVEL_LABEL.get(res_lvl, res_lvl.upper()),
            _STATUS_LABEL.get(str(risk.get("status") or "ouvert"), str(risk.get("status") or "")),
            str(risk.get("owner") or ""),
            str(risk.get("review_date") or ""),
        ]
        style: list[str | None] = [
            None, style_key, None, None, None,
            None, None, None, style_key, style_key,
            None,
            None, None, res_style, res_style,
            None, None, None,
        ]
        data_rows.append(row)
        data_styles.append(style)

    all_rows = [summary_row1, summary_row2, summary_row3, summary_row4] + data_rows
    all_styles: list[list[str | None]] = [[], [], [], []] + data_styles

    filename = f"registre_risques_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    path = _unique_path(filename)
    write_styled_xlsx(
        path,
        sheet_name="Registre des Risques",
        headers=headers,
        rows=all_rows,
        styles=all_styles,
        document_title="OREZONE QHSE - RISK REGISTER",
    )
    return path


def export_risk_register_pdf(
    status: str | None = None,
    level: str | None = None,
    hazard_type: str | None = None,
) -> Path:
    risks = list_risks(status=status, level=level, hazard_type=hazard_type)
    summary = get_risk_summary()
    heatmap = get_risk_heatmap()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    filename = f"registre_risques_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = _unique_path(filename)
    try:
        _write_risk_pdf(path, risks, summary, heatmap, generated_at)
    except Exception:
        _write_risk_pdf_fallback(path, risks, summary, generated_at)
    return path


def _level_color_hex(level: str) -> str:
    return {
        "critique": "#EF4444",
        "eleve": "#F97316",
        "moyen": "#F59E0B",
        "faible": "#10B981",
    }.get(level, "#64748B")


def _write_risk_pdf(
    path: Path,
    risks: list[dict[str, Any]],
    summary: dict[str, Any],
    heatmap: dict[tuple[int, int], int],
    generated_at: str,
) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    styles_rl = getSampleStyleSheet()

    navy = colors.HexColor("#0D2040")
    dark_head = colors.HexColor("#112240")
    primary = colors.HexColor("#3B82F6")
    c_critique = colors.HexColor("#EF4444")
    c_eleve = colors.HexColor("#F97316")
    c_moyen = colors.HexColor("#F59E0B")
    c_faible = colors.HexColor("#10B981")
    white = colors.white
    light_grey = colors.HexColor("#E2E8F0")

    level_colors = {
        "critique": c_critique,
        "eleve": c_eleve,
        "moyen": c_moyen,
        "faible": c_faible,
    }

    title_style = ParagraphStyle(
        "RiskTitle", parent=styles_rl["Title"],
        fontName="Helvetica-Bold", fontSize=18, leading=22,
        textColor=white, alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "RiskSubtitle", parent=styles_rl["Normal"],
        fontName="Helvetica", fontSize=9, leading=11,
        textColor=colors.HexColor("#9DB0C5"), alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "RiskSection", parent=styles_rl["Normal"],
        fontName="Helvetica-Bold", fontSize=11, leading=14,
        textColor=primary,
    )
    cell_style = ParagraphStyle(
        "RiskCell", parent=styles_rl["Normal"],
        fontName="Helvetica", fontSize=7.5, leading=9,
        textColor=colors.HexColor("#E2E8F0"),
    )
    cell_bold = ParagraphStyle(
        "RiskCellBold", parent=cell_style,
        fontName="Helvetica-Bold",
    )

    doc = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )

    story = []

    # ── Header banner ──────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("OREZONE QHSE", title_style),
        Paragraph(
            "REGISTRE DES RISQUES<br/>"
            "<font size='9'>ISO 31000:2018 · ISO 45001:2018 · Matrice de Criticité 5×5</font>",
            title_style,
        ),
        Paragraph(f"Généré le<br/>{generated_at}", subtitle_style),
    ]]
    header_table = Table(header_data, colWidths=[50 * mm, 130 * mm, 50 * mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), navy),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [navy]),
        ("BOX", (0, 0), (-1, -1), 0.5, primary),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6 * mm))

    # ── KPI summary ────────────────────────────────────────────────────────────
    kpi_data = [[
        Paragraph(f"<b>{summary.get('total', 0)}</b><br/>Total risques", cell_bold),
        Paragraph(f"<b><font color='#EF4444'>{summary.get('critique', 0)}</font></b><br/>Critiques", cell_bold),
        Paragraph(f"<b><font color='#F97316'>{summary.get('eleve', 0)}</font></b><br/>Élevés", cell_bold),
        Paragraph(f"<b><font color='#F59E0B'>{summary.get('moyen', 0)}</font></b><br/>Moyens", cell_bold),
        Paragraph(f"<b><font color='#10B981'>{summary.get('faible', 0)}</font></b><br/>Faibles", cell_bold),
        Paragraph(f"<b>{summary.get('ouvert', 0)}</b><br/>Ouverts", cell_bold),
        Paragraph(f"<b>{summary.get('en_cours', 0)}</b><br/>En cours", cell_bold),
        Paragraph(f"<b>{summary.get('clos', 0)}</b><br/>Clos", cell_bold),
    ]]
    kpi_table = Table(kpi_data, colWidths=[29 * mm] * 8)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), dark_head),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#1E3A5F")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#1E3A5F")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (0, 0), (-1, -1), light_grey),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 5 * mm))

    # ── Risk register table ────────────────────────────────────────────────────
    story.append(Paragraph("Registre des Risques", section_style))
    story.append(Spacer(1, 3 * mm))

    col_headers = [
        "N°", "Titre", "Activité", "Type Danger",
        "P", "G", "Score", "Niveau",
        "Mesures Existantes",
        "P Rés.", "G Rés.", "Score Rés.", "Niv. Rés.",
        "Statut", "Responsable", "Révision",
    ]
    col_w = [
        8 * mm, 38 * mm, 22 * mm, 18 * mm,
        6 * mm, 6 * mm, 10 * mm, 14 * mm,
        36 * mm,
        6 * mm, 6 * mm, 10 * mm, 14 * mm,
        13 * mm, 18 * mm, 16 * mm,
    ]

    header_row = [Paragraph(h, cell_bold) for h in col_headers]
    table_data: list[list[Any]] = [header_row]
    table_styles: list[tuple[Any, ...]] = [
        ("BACKGROUND", (0, 0), (-1, 0), dark_head),
        ("TEXTCOLOR", (0, 0), (-1, 0), primary),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#1E3A5F")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#1E3A5F")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("ALIGN", (8, 1), (8, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#0D2040"), colors.HexColor("#0A1929")]),
    ]

    for row_idx, risk in enumerate(risks, start=1):
        lvl = str(risk.get("risk_level") or "faible")
        res_lvl = str(risk.get("residual_level") or "faible")
        lvl_clr = level_colors.get(lvl, colors.HexColor("#64748B"))
        res_clr = level_colors.get(res_lvl, colors.HexColor("#64748B"))

        row_data = [
            Paragraph(str(risk.get("id", "")), cell_style),
            Paragraph(str(risk.get("title") or "")[:60], cell_style),
            Paragraph(str(risk.get("activity") or "")[:28], cell_style),
            Paragraph(str(risk.get("hazard_type") or "")[:20], cell_style),
            Paragraph(str(risk.get("probability", "")), cell_style),
            Paragraph(str(risk.get("severity", "")), cell_style),
            Paragraph(str(risk.get("risk_score", "")), cell_bold),
            Paragraph(_LEVEL_LABEL.get(lvl, lvl.upper()), cell_bold),
            Paragraph(str(risk.get("existing_controls") or "")[:80], cell_style),
            Paragraph(str(risk.get("residual_probability", "")), cell_style),
            Paragraph(str(risk.get("residual_severity", "")), cell_style),
            Paragraph(str(risk.get("residual_score", "")), cell_bold),
            Paragraph(_LEVEL_LABEL.get(res_lvl, res_lvl.upper()), cell_bold),
            Paragraph(_STATUS_LABEL.get(str(risk.get("status") or ""), ""), cell_style),
            Paragraph(str(risk.get("owner") or "")[:20], cell_style),
            Paragraph(str(risk.get("review_date") or ""), cell_style),
        ]
        table_data.append(row_data)
        table_styles.append(("TEXTCOLOR", (7, row_idx), (7, row_idx), lvl_clr))
        table_styles.append(("TEXTCOLOR", (11, row_idx), (12, row_idx), res_clr))

    risk_table = Table(table_data, colWidths=col_w, repeatRows=1)
    risk_table.setStyle(TableStyle(table_styles))
    story.append(risk_table)
    story.append(Spacer(1, 5 * mm))

    # ── Footer ─────────────────────────────────────────────────────────────────
    footer_data = [["Préparé par", "Vérifié par", "Approuvé par"]]
    footer_data.append(["______________________", "______________________", "______________________"])
    footer_table = Table(footer_data, colWidths=[79 * mm] * 3)
    footer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), dark_head),
        ("TEXTCOLOR", (0, 0), (-1, 0), primary),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#1E3A5F")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#1E3A5F")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TEXTCOLOR", (0, 1), (-1, 1), light_grey),
    ]))
    story.append(footer_table)

    doc.build(story)


def _write_risk_pdf_fallback(
    path: Path,
    risks: list[dict[str, Any]],
    summary: dict[str, Any],
    generated_at: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "OREZONE QHSE — REGISTRE DES RISQUES",
        f"ISO 31000:2018 | Généré le {generated_at}",
        "",
        f"Total: {summary.get('total',0)} | Critiques: {summary.get('critique',0)} | Élevés: {summary.get('eleve',0)} | Moyens: {summary.get('moyen',0)} | Faibles: {summary.get('faible',0)}",
        "",
        " | ".join(["N°", "Titre", "Type", "P", "G", "Score", "Niveau", "Statut", "Responsable"]),
        "-" * 100,
    ]
    for r in risks:
        lines.append(" | ".join([
            str(r.get("id", "")),
            str(r.get("title") or "")[:40],
            str(r.get("hazard_type") or ""),
            str(r.get("probability", "")),
            str(r.get("severity", "")),
            str(r.get("risk_score", "")),
            _LEVEL_LABEL.get(str(r.get("risk_level") or ""), ""),
            _STATUS_LABEL.get(str(r.get("status") or ""), ""),
            str(r.get("owner") or ""),
        ]))
    lines += ["", "Préparé par: __________ Vérifié par: __________ Approuvé par: __________"]
    path.write_text("\n".join(lines), encoding="utf-8")


def export_risk_fiche_pdf(risk_id: int) -> Path:
    """Export a single risk as a detailed one-page A4 fiche."""
    from app.services.risk_service import get_risk, list_controls
    risk = get_risk(risk_id)
    if not risk:
        raise ValueError(f"Risque {risk_id} introuvable")
    controls = list_controls(risk_id)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    title_safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in str(risk.get("title") or "risque"))[:30]
    filename = f"fiche_risque_{risk_id}_{title_safe}_{datetime.now().strftime('%Y%m%d')}.pdf"
    path = _unique_path(filename)
    try:
        _write_fiche_pdf(path, risk, controls, generated_at)
    except Exception:
        _write_fiche_pdf_fallback(path, risk, controls, generated_at)
    return path


def _write_fiche_pdf(
    path: Path,
    risk: dict[str, Any],
    controls: list[dict[str, Any]],
    generated_at: str,
) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    styles_rl = getSampleStyleSheet()

    navy = colors.HexColor("#0D2040")
    dark_head = colors.HexColor("#112240")
    primary = colors.HexColor("#3B82F6")
    c_critique = colors.HexColor("#EF4444")
    c_eleve = colors.HexColor("#F97316")
    c_moyen = colors.HexColor("#F59E0B")
    c_faible = colors.HexColor("#10B981")
    white = colors.white
    light_grey = colors.HexColor("#E2E8F0")
    mid_grey = colors.HexColor("#1E3A5F")

    level_colors = {
        "critique": c_critique,
        "eleve": c_eleve,
        "moyen": c_moyen,
        "faible": c_faible,
    }

    status_control_colors = {
        "planifie": colors.HexColor("#F59E0B"),
        "en_cours": colors.HexColor("#3B82F6"),
        "realise": colors.HexColor("#10B981"),
    }

    title_style = ParagraphStyle(
        "FicheTitle", parent=styles_rl["Title"],
        fontName="Helvetica-Bold", fontSize=16, leading=20,
        textColor=white, alignment=TA_LEFT,
    )
    title_right_style = ParagraphStyle(
        "FicheTitleRight", parent=styles_rl["Normal"],
        fontName="Helvetica", fontSize=9, leading=12,
        textColor=colors.HexColor("#9DB0C5"), alignment=TA_RIGHT,
    )
    subtitle_style = ParagraphStyle(
        "FicheSubtitle", parent=styles_rl["Normal"],
        fontName="Helvetica", fontSize=8, leading=10,
        textColor=colors.HexColor("#9DB0C5"), alignment=TA_LEFT,
    )
    section_style = ParagraphStyle(
        "FicheSection", parent=styles_rl["Normal"],
        fontName="Helvetica-Bold", fontSize=10, leading=13,
        textColor=primary,
    )
    cell_style = ParagraphStyle(
        "FicheCell", parent=styles_rl["Normal"],
        fontName="Helvetica", fontSize=8, leading=10,
        textColor=light_grey,
    )
    cell_bold = ParagraphStyle(
        "FicheCellBold", parent=cell_style,
        fontName="Helvetica-Bold",
    )
    label_style = ParagraphStyle(
        "FicheLabel", parent=styles_rl["Normal"],
        fontName="Helvetica-Bold", fontSize=7.5, leading=9,
        textColor=colors.HexColor("#9DB0C5"),
    )

    usable_width = A4[0] - 24 * mm  # left+right margin = 12mm each

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )

    story: list[Any] = []

    # ── Header banner ──────────────────────────────────────────────────────────
    risk_id_val = risk.get("id", "")
    header_data = [[
        Paragraph(
            "OREZONE QHSE<br/>"
            "<font size='8'>FICHE D'ANALYSE DE RISQUE</font>",
            title_style,
        ),
        Paragraph(
            f"N° {risk_id_val} | {generated_at}",
            title_right_style,
        ),
    ]]
    header_table = Table(header_data, colWidths=[usable_width * 0.65, usable_width * 0.35])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), navy),
        ("BOX", (0, 0), (-1, -1), 0.5, primary),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (0, -1), 10),
        ("RIGHTPADDING", (1, 0), (1, -1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    # ── Section 1 — Identification ─────────────────────────────────────────────
    story.append(Paragraph("1. Identification", section_style))
    story.append(Spacer(1, 2 * mm))

    lvl = str(risk.get("risk_level") or "faible")
    lvl_color = level_colors.get(lvl, colors.HexColor("#64748B"))
    lvl_hex = _level_color_hex(lvl)

    title_val = str(risk.get("title") or "—")
    activity_val = str(risk.get("activity") or "—")
    zone_val = str(risk.get("zone") or "—")
    hazard_type_val = str(risk.get("hazard_type") or "—")
    affected_val = str(risk.get("affected_people") or "—")
    danger_source_val = str(risk.get("danger_source") or "—")

    half = usable_width / 2

    id_data = [
        [
            Paragraph(f"<b><font color='{lvl_hex}'>{title_val}</font></b>", cell_bold),
            "",
        ],
        [
            Paragraph(f"<b>Activité :</b> {activity_val}", cell_style),
            Paragraph(f"<b>Zone :</b> {zone_val}", cell_style),
        ],
        [
            Paragraph(f"<b>Type de danger :</b> {hazard_type_val}", cell_style),
            Paragraph(f"<b>Personnes exposées :</b> {affected_val}", cell_style),
        ],
        [
            Paragraph(f"<b>Source du danger :</b> {danger_source_val}", cell_style),
            "",
        ],
    ]
    id_table = Table(id_data, colWidths=[half, half])
    id_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), dark_head),
        ("BOX", (0, 0), (-1, -1), 0.5, mid_grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, mid_grey),
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (0, 3), (1, 3)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(id_table)
    story.append(Spacer(1, 4 * mm))

    # ── Section 2 — Évaluation initiale ───────────────────────────────────────
    story.append(Paragraph("2. Évaluation initiale", section_style))
    story.append(Spacer(1, 2 * mm))

    prob = risk.get("probability", "—")
    sev = risk.get("severity", "—")
    score = risk.get("risk_score", "—")
    existing_controls_val = str(risk.get("existing_controls") or "—")

    eval_left = Paragraph(
        f"<b>P = {prob} × G = {sev} = Score {score}</b><br/>"
        f"<font color='{lvl_hex}'><b>NIVEAU {_LEVEL_LABEL.get(lvl, lvl.upper())}</b></font>",
        cell_bold,
    )
    eval_right = Paragraph(
        f"<b>Mesures existantes :</b><br/>{existing_controls_val}",
        cell_style,
    )

    eval_data = [[eval_left, eval_right]]
    eval_table = Table(eval_data, colWidths=[half, half])
    eval_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#0A1929")),
        ("BACKGROUND", (1, 0), (1, 0), dark_head),
        ("BOX", (0, 0), (-1, -1), 0.5, mid_grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, mid_grey),
        ("LINEAFTER", (0, 0), (0, -1), 1, lvl_color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(eval_table)
    story.append(Spacer(1, 4 * mm))

    # ── Section 3 — Risque résiduel ────────────────────────────────────────────
    story.append(Paragraph("3. Risque résiduel", section_style))
    story.append(Spacer(1, 2 * mm))

    res_prob = risk.get("residual_probability", "—")
    res_sev = risk.get("residual_severity", "—")
    res_score = risk.get("residual_score", "—")
    res_lvl = str(risk.get("residual_level") or "faible")
    res_lvl_color = level_colors.get(res_lvl, colors.HexColor("#64748B"))
    res_lvl_hex = _level_color_hex(res_lvl)

    res_left = Paragraph(
        f"<b>P = {res_prob} × G = {res_sev} = Score {res_score}</b><br/>"
        f"<font color='{res_lvl_hex}'><b>NIVEAU {_LEVEL_LABEL.get(res_lvl, res_lvl.upper())}</b></font>",
        cell_bold,
    )
    res_right = Paragraph("—", cell_style)

    res_data = [[res_left, res_right]]
    res_table = Table(res_data, colWidths=[half, half])
    res_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#0A1929")),
        ("BACKGROUND", (1, 0), (1, 0), dark_head),
        ("BOX", (0, 0), (-1, -1), 0.5, mid_grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, mid_grey),
        ("LINEAFTER", (0, 0), (0, -1), 1, res_lvl_color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(res_table)
    story.append(Spacer(1, 4 * mm))

    # ── Section 4 — Plan de maîtrise ──────────────────────────────────────────
    story.append(Paragraph("4. Plan de maîtrise", section_style))
    story.append(Spacer(1, 2 * mm))

    if controls:
        ctrl_headers = ["Type", "Description", "Responsable", "Échéance", "Statut"]
        ctrl_col_w = [
            usable_width * 0.13,
            usable_width * 0.40,
            usable_width * 0.17,
            usable_width * 0.15,
            usable_width * 0.15,
        ]
        ctrl_header_row = [Paragraph(h, cell_bold) for h in ctrl_headers]
        ctrl_data: list[list[Any]] = [ctrl_header_row]
        ctrl_styles: list[tuple[Any, ...]] = [
            ("BACKGROUND", (0, 0), (-1, 0), dark_head),
            ("TEXTCOLOR", (0, 0), (-1, 0), primary),
            ("BOX", (0, 0), (-1, -1), 0.5, mid_grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, mid_grey),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("ALIGN", (2, 0), (4, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#0D2040"), colors.HexColor("#0A1929")]),
        ]
        for row_idx, ctrl in enumerate(controls, start=1):
            ctrl_status = str(ctrl.get("status") or "planifie")
            status_clr = status_control_colors.get(ctrl_status, light_grey)
            status_label_map = {"planifie": "Planifié", "en_cours": "En cours", "realise": "Réalisé"}
            ctrl_row = [
                Paragraph(str(ctrl.get("control_type") or "—"), cell_style),
                Paragraph(str(ctrl.get("description") or "—"), cell_style),
                Paragraph(str(ctrl.get("responsible") or "—"), cell_style),
                Paragraph(str(ctrl.get("due_date") or "—"), cell_style),
                Paragraph(status_label_map.get(ctrl_status, ctrl_status), cell_bold),
            ]
            ctrl_data.append(ctrl_row)
            ctrl_styles.append(("TEXTCOLOR", (4, row_idx), (4, row_idx), status_clr))
        ctrl_table = Table(ctrl_data, colWidths=ctrl_col_w, repeatRows=1)
        ctrl_table.setStyle(TableStyle(ctrl_styles))
        story.append(ctrl_table)
    else:
        story.append(Paragraph("Aucune mesure de maîtrise enregistrée.", cell_style))

    story.append(Spacer(1, 4 * mm))

    # ── Section 5 — Informations administratives ──────────────────────────────
    story.append(Paragraph("5. Informations administratives", section_style))
    story.append(Spacer(1, 2 * mm))

    risk_status_val = _STATUS_LABEL.get(str(risk.get("status") or "ouvert"), str(risk.get("status") or "—"))
    owner_val = str(risk.get("owner") or "—")
    review_date_val = str(risk.get("review_date") or "—")
    created_at_val = str(risk.get("created_at") or "—")

    quarter = usable_width / 4
    admin_data = [[
        Paragraph(f"<b>Statut</b><br/>{risk_status_val}", cell_style),
        Paragraph(f"<b>Responsable</b><br/>{owner_val}", cell_style),
        Paragraph(f"<b>Date de révision</b><br/>{review_date_val}", cell_style),
        Paragraph(f"<b>Créé le</b><br/>{created_at_val}", cell_style),
    ]]
    admin_table = Table(admin_data, colWidths=[quarter, quarter, quarter, quarter])
    admin_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), dark_head),
        ("BOX", (0, 0), (-1, -1), 0.5, mid_grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, mid_grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TEXTCOLOR", (0, 0), (-1, -1), light_grey),
    ]))
    story.append(admin_table)
    story.append(Spacer(1, 5 * mm))

    # ── Footer: signature boxes ────────────────────────────────────────────────
    footer_data = [["Préparé par", "Vérifié par", "Approuvé par"]]
    footer_data.append(["______________________", "______________________", "______________________"])
    third = usable_width / 3
    footer_table = Table(footer_data, colWidths=[third, third, third])
    footer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), dark_head),
        ("TEXTCOLOR", (0, 0), (-1, 0), primary),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.5, mid_grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, mid_grey),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TEXTCOLOR", (0, 1), (-1, 1), light_grey),
    ]))
    story.append(footer_table)

    doc.build(story)


def _write_fiche_pdf_fallback(
    path: Path,
    risk: dict[str, Any],
    controls: list[dict[str, Any]],
    generated_at: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lvl = str(risk.get("risk_level") or "faible")
    res_lvl = str(risk.get("residual_level") or "faible")
    lines = [
        "OREZONE QHSE — FICHE D'ANALYSE DE RISQUE",
        f"N° {risk.get('id', '')} | Généré le {generated_at}",
        "=" * 70,
        "",
        "1. IDENTIFICATION",
        f"  Titre         : {risk.get('title') or '—'}",
        f"  Activité      : {risk.get('activity') or '—'}",
        f"  Zone          : {risk.get('zone') or '—'}",
        f"  Type de danger: {risk.get('hazard_type') or '—'}",
        f"  Personnes exp.: {risk.get('affected_people') or '—'}",
        f"  Source danger : {risk.get('danger_source') or '—'}",
        "",
        "2. ÉVALUATION INITIALE",
        f"  P={risk.get('probability','—')} × G={risk.get('severity','—')} = Score {risk.get('risk_score','—')}",
        f"  Niveau        : {_LEVEL_LABEL.get(lvl, lvl.upper())}",
        f"  Mesures exist.: {risk.get('existing_controls') or '—'}",
        "",
        "3. RISQUE RÉSIDUEL",
        f"  P={risk.get('residual_probability','—')} × G={risk.get('residual_severity','—')} = Score {risk.get('residual_score','—')}",
        f"  Niveau résid. : {_LEVEL_LABEL.get(res_lvl, res_lvl.upper())}",
        "",
        "4. PLAN DE MAÎTRISE",
    ]
    if controls:
        lines.append("  " + " | ".join(["Type", "Description", "Responsable", "Échéance", "Statut"]))
        lines.append("  " + "-" * 60)
        for ctrl in controls:
            status_label_map = {"planifie": "Planifié", "en_cours": "En cours", "realise": "Réalisé"}
            ctrl_status = str(ctrl.get("status") or "planifie")
            lines.append("  " + " | ".join([
                str(ctrl.get("control_type") or "—"),
                str(ctrl.get("description") or "—")[:40],
                str(ctrl.get("responsible") or "—"),
                str(ctrl.get("due_date") or "—"),
                status_label_map.get(ctrl_status, ctrl_status),
            ]))
    else:
        lines.append("  Aucune mesure de maîtrise enregistrée.")
    lines += [
        "",
        "5. INFORMATIONS ADMINISTRATIVES",
        f"  Statut        : {_STATUS_LABEL.get(str(risk.get('status') or ''), '—')}",
        f"  Responsable   : {risk.get('owner') or '—'}",
        f"  Date révision : {risk.get('review_date') or '—'}",
        f"  Créé le       : {risk.get('created_at') or '—'}",
        "",
        "Préparé par: __________ Vérifié par: __________ Approuvé par: __________",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def open_export_file(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass
