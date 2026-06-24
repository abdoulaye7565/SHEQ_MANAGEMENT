from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import EXPORTS_DIR

_LOGGER = logging.getLogger(__name__)


def open_dotation_file(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as _exc:
        _LOGGER.warning("Impossible d'ouvrir le fichier de dotation %s: %s", path, _exc)


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


def export_ppe_dotation_sheet_pdf(
    employees: list[dict[str, Any]],
    ppe_items: list[dict[str, Any]],
    issue_date: str,
    issued_by: str = "",
    observation: str = "",
) -> Path:
    """
    Generate a printable PPE dotation sheet PDF.
    One page per employee. Each page contains employee info, PPE table, and signature zones.

    employees: list of dicts with keys: nom, prenom, matricule, badge, fonction, site
    ppe_items: list of dicts with keys: label (str), quantite (int), taille (str), norme (str), etat (str)
    issue_date: YYYY-MM-DD string
    issued_by: name of person issuing (responsible)
    observation: free text
    """
    ref_num = f"DOT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    filename = f"fiche_dotation_epi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = _unique_path(filename)
    try:
        _write_dotation_pdf(path, employees, ppe_items, issue_date, issued_by, observation, ref_num)
    except Exception:
        _write_dotation_fallback(path, employees, ppe_items, issue_date, issued_by, ref_num)
    return path


def _write_dotation_pdf(
    path: Path,
    employees: list[dict[str, Any]],
    ppe_items: list[dict[str, Any]],
    issue_date: str,
    issued_by: str,
    observation: str,
    ref_num: str,
) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    rl_styles = getSampleStyleSheet()

    # Color palette
    navy     = colors.HexColor("#0D2040")
    mid_navy = colors.HexColor("#112240")
    primary  = colors.HexColor("#3B82F6")
    success  = colors.HexColor("#10B981")
    danger   = colors.HexColor("#EF4444")
    warning  = colors.HexColor("#F59E0B")
    light    = colors.HexColor("#E2E8F0")
    white    = colors.white
    muted    = colors.HexColor("#9DB0C5")
    row_alt  = colors.HexColor("#F0F4F8")

    # Styles
    title_s = ParagraphStyle("DotTitle", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=white, alignment=TA_CENTER)
    sub_s   = ParagraphStyle("DotSub",   fontName="Helvetica",      fontSize=8,  leading=10, textColor=muted,  alignment=TA_CENTER)
    ref_s   = ParagraphStyle("DotRef",   fontName="Helvetica",      fontSize=8,  leading=10, textColor=white,  alignment=TA_RIGHT)
    head_s  = ParagraphStyle("DotHead",  fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=navy)
    cell_s  = ParagraphStyle("DotCell",  fontName="Helvetica",      fontSize=8.5,leading=11, textColor=colors.HexColor("#1E293B"))
    small_s = ParagraphStyle("DotSmall", fontName="Helvetica",      fontSize=7.5,leading=9,  textColor=colors.HexColor("#334155"))
    cert_s  = ParagraphStyle("DotCert",  fontName="Helvetica-Oblique", fontSize=8, leading=11, textColor=colors.HexColor("#1E293B"))
    sig_hd  = ParagraphStyle("DotSigH",  fontName="Helvetica-Bold", fontSize=8,  leading=10, textColor=navy, alignment=TA_CENTER)
    sig_sub = ParagraphStyle("DotSigS",  fontName="Helvetica",      fontSize=7,  leading=9,  textColor=muted, alignment=TA_CENTER)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )

    page_w = A4[0] - 30 * mm
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    issue_display = issue_date.replace("-", "/") if issue_date else generated_at[:10]

    story = []

    for idx, emp in enumerate(employees):
        if idx > 0:
            story.append(PageBreak())

        emp_name = f"{emp.get('nom', '')} {emp.get('prenom', '')}".strip()

        # -- Header banner --
        header_table = Table(
            [[
                Paragraph("OREZONE QHSE", title_s),
                Paragraph(
                    "BON DE DOTATION EN ÉQUIPEMENTS DE PROTECTION INDIVIDUELLE (EPI)",
                    title_s,
                ),
                Paragraph(f"{ref_num}<br/>{generated_at}", ref_s),
            ]],
            colWidths=[page_w * 0.18, page_w * 0.64, page_w * 0.18],
        )
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), navy),
            ("TOPPADDING",  (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 5 * mm))

        # -- Employee info --
        story.append(Paragraph("INFORMATIONS DU BÉNÉFICIAIRE", head_s))
        story.append(Spacer(1, 2 * mm))

        emp_rows = [
            ["Nom & Prénom", emp_name, "Date de remise", issue_display],
            ["Matricule", emp.get("matricule") or "—", "Badge", emp.get("badge") or "—"],
            ["Fonction", emp.get("fonction") or "—", "Site / Département", emp.get("site") or "—"],
        ]
        emp_table = Table(
            [[Paragraph(c if i % 2 == 0 else c, cell_s if i % 2 != 0 else small_s) for i, c in enumerate(row)] for row in emp_rows],
            colWidths=[page_w * 0.18, page_w * 0.32, page_w * 0.18, page_w * 0.32],
        )
        emp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), light),
            ("BACKGROUND", (2, 0), (2, -1), light),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TEXTCOLOR", (0, 0), (0, -1), navy),
            ("TEXTCOLOR", (2, 0), (2, -1), navy),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(emp_table)
        story.append(Spacer(1, 4 * mm))

        # -- PPE table --
        story.append(Paragraph("ÉQUIPEMENTS DE PROTECTION INDIVIDUELLE REMIS", head_s))
        story.append(Spacer(1, 2 * mm))

        ppe_header = ["N°", "Type d'EPI", "Désignation", "Taille", "Norme", "Qté", "État", "Date remise", "Exp."]
        ppe_col_w  = [
            page_w * 0.04,
            page_w * 0.13,
            page_w * 0.22,
            page_w * 0.07,
            page_w * 0.10,
            page_w * 0.05,
            page_w * 0.08,
            page_w * 0.11,
            page_w * 0.10,
        ]
        ppe_data = [ppe_header]
        etat_labels = {"neuf": "Neuf", "bon": "Bon", "usage": "Usagé", "endommage": "Endommagé"}
        for i, item in enumerate(ppe_items, 1):
            etat = str(item.get("etat") or "neuf")
            raw_label = str(item.get("label", ""))
            type_epi = str(item.get("type_epi") or (raw_label.split(" - ")[0] if " - " in raw_label else raw_label))
            item_date = str(item.get("date_remise") or issue_date or "").replace("-", "/") or issue_display
            ppe_data.append([
                str(i),
                type_epi,
                str(item.get("designation") or item.get("label") or item.get("epi_nom") or "—"),
                str(item.get("taille") or "—"),
                str(item.get("norme") or "—"),
                str(item.get("quantite") or 1),
                etat_labels.get(etat, etat.title()),
                item_date,
                str(item.get("date_expiration") or "—"),
            ])

        ppe_table = Table(ppe_data, colWidths=ppe_col_w)
        ppe_ts = [
            ("BACKGROUND", (0, 0), (-1, 0), mid_navy),
            ("TEXTCOLOR",  (0, 0), (-1, 0), white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("ALIGN",      (2, 1), (2, -1), "LEFT"),
            ("ALIGN",      (1, 1), (1, -1), "LEFT"),
            ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ]
        for row_i in range(1, len(ppe_data)):
            if row_i % 2 == 0:
                ppe_ts.append(("BACKGROUND", (0, row_i), (-1, row_i), row_alt))
        ppe_table.setStyle(TableStyle(ppe_ts))
        story.append(ppe_table)
        story.append(Spacer(1, 3 * mm))

        # Observation
        if observation:
            story.append(Paragraph(f"<b>Observation :</b> {observation}", small_s))
            story.append(Spacer(1, 2 * mm))

        # -- Certification text --
        story.append(HRFlowable(width=page_w, thickness=0.5, color=colors.HexColor("#CBD5E1")))
        story.append(Spacer(1, 2 * mm))
        item_dates = {str(it.get("date_remise") or "").replace("-", "/") for it in ppe_items if it.get("date_remise")}
        if len(item_dates) == 1:
            date_clause = f"à la date du <b>{next(iter(item_dates))}</b>"
        else:
            date_clause = "aux dates indiquées dans le tableau ci-dessus"
        cert_text = (
            f"Je soussigné(e) <b>{emp_name}</b>, certifie avoir reçu les Équipements de Protection Individuelle (EPI) "
            f"listés ci-dessus en bon état et en quantité correcte, {date_clause}. "
            "Je m'engage à les utiliser conformément aux consignes de sécurité en vigueur, à les entretenir "
            "correctement et à signaler immédiatement tout défaut ou dommage constaté. "
            "Ces EPI sont fournis dans le cadre de l'exercice de mes fonctions et restent la propriété de l'entreprise."
        )
        story.append(Paragraph(cert_text, cert_s))
        story.append(Spacer(1, 5 * mm))

        # -- Signature boxes --
        sig_labels = [
            ("Employé / Bénéficiaire", emp_name),
            ("Responsable Hiérarchique", issued_by or ""),
            ("Responsable HSE", ""),
            ("Magasinier / Émetteur", ""),
        ]
        sig_cells = []
        for sig_title, sig_name in sig_labels:
            sig_cells.append(
                Table(
                    [
                        [Paragraph(sig_title, sig_hd)],
                        [Paragraph(sig_name, sig_sub)],
                        [Paragraph("", sig_sub)],
                        [Paragraph("", sig_sub)],
                        [Paragraph("Date : ___/___/______", sig_sub)],
                        [Paragraph("Signature :", sig_sub)],
                        [Paragraph("", sig_sub)],
                        [Paragraph("", sig_sub)],
                        [Paragraph("_________________________", sig_sub)],
                    ],
                    colWidths=[page_w / 4 - 4 * mm],
                    rowHeights=[None, None, 3*mm, 8*mm, None, None, 3*mm, 8*mm, None],
                )
            )
            sig_cells[-1].setStyle(TableStyle([
                ("BOX",     (0, 0), (-1, -1), 0.8, colors.HexColor("#94A3B8")),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING",   (0, 0), (-1, -1), 5),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
            ]))

        sig_table = Table([sig_cells], colWidths=[page_w / 4] * 4)
        sig_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(sig_table)
        story.append(Spacer(1, 3 * mm))

        # -- Footer --
        footer_table = Table(
            [[
                Paragraph(f"Réf : {ref_num}", small_s),
                Paragraph("OREZONE QHSE — Document confidentiel interne", ParagraphStyle("FC", fontName="Helvetica", fontSize=7, alignment=TA_CENTER, textColor=muted)),
                Paragraph(f"Page {idx+1}/{len(employees)} — Généré le {generated_at}", ParagraphStyle("FR", fontName="Helvetica", fontSize=7, alignment=TA_RIGHT, textColor=muted)),
            ]],
            colWidths=[page_w * 0.25, page_w * 0.50, page_w * 0.25],
        )
        footer_table.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("LINEABOVE", (0, 0), (-1, 0), 0.4, colors.HexColor("#CBD5E1")),
        ]))
        story.append(footer_table)

    doc.build(story)


def _write_dotation_fallback(
    path: Path,
    employees: list[dict[str, Any]],
    ppe_items: list[dict[str, Any]],
    issue_date: str,
    issued_by: str,
    ref_num: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"BON DE DOTATION EPI — {ref_num}", f"Date: {issue_date}", f"Emis par: {issued_by}", "=" * 60, ""]
    for emp in employees:
        lines.append(f"Employé: {emp.get('nom', '')} {emp.get('prenom', '')}")
        lines.append(f"Matricule: {emp.get('matricule', '')} | Badge: {emp.get('badge', '')}")
        lines.append(f"Fonction: {emp.get('fonction', '')} | Site: {emp.get('site', '')}")
        lines.append("EPI remis:")
        for i, item in enumerate(ppe_items, 1):
            item_date = str(item.get("date_remise") or issue_date or "")
            lines.append(f"  {i}. {item.get('label', '')} x{item.get('quantite', 1)} — Date: {item_date}")
        lines.extend(["", "-" * 60, ""])
    path.with_suffix(".txt").write_text("\n".join(lines), encoding="utf-8")
    path.rename(path)  # keep .pdf extension but write text
