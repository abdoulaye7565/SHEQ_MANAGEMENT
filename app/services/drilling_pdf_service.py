"""
Génère un PDF qui reproduit exactement le formulaire papier
AC/RC DRILL DAILY OPERATOR REPORT – OREZONE.
"""
from __future__ import annotations

import io
from typing import Any

import base64

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.utils import ImageReader

# ── Colours ───────────────────────────────────────────────────────────────────
_NAVY   = colors.HexColor("#1E3A8A")
_BLACK  = colors.black
_WHITE  = colors.white
_LGREY  = colors.HexColor("#F5F5F5")
_MGREY  = colors.HexColor("#D0D0D0")
_DGREY  = colors.HexColor("#808080")

# ── Paragraph styles ──────────────────────────────────────────────────────────
_TITLE_ST = ParagraphStyle(
    "title",
    fontName="Helvetica-Bold",
    fontSize=13,
    textColor=_BLACK,
    spaceAfter=0,
    leading=15,
)
_ORE_ST = ParagraphStyle(
    "ore",
    fontName="Helvetica-Bold",
    fontSize=13,
    textColor=_NAVY,
    alignment=2,  # right
)
_HEAD_ST = ParagraphStyle(
    "head",
    fontName="Helvetica-Bold",
    fontSize=8,
    textColor=_WHITE,
)
_CELL_ST = ParagraphStyle(
    "cell",
    fontName="Helvetica",
    fontSize=8,
    textColor=_BLACK,
    leading=10,
)
_LABEL_ST = ParagraphStyle(
    "label",
    fontName="Helvetica-Bold",
    fontSize=8,
    textColor=_BLACK,
)
_VAL_ST = ParagraphStyle(
    "val",
    fontName="Helvetica",
    fontSize=9,
    textColor=_BLACK,
)
_FOOT_ST = ParagraphStyle(
    "foot",
    fontName="Helvetica",
    fontSize=7,
    textColor=_DGREY,
)
_SEC_ST = ParagraphStyle(
    "sec",
    fontName="Helvetica-Bold",
    fontSize=9,
    textColor=_WHITE,
)


def _p(text: str, style: ParagraphStyle = _CELL_ST) -> Paragraph:
    return Paragraph(str(text or ""), style)


def _fmt(val: Any, suffix: str = "") -> str:
    if val is None or val == "":
        return ""
    return f"{val}{suffix}"


# ── Main builder ──────────────────────────────────────────────────────────────

def build_drilling_pdf(report: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=15 * mm,
    )

    W = A4[0] - 30 * mm   # usable width
    story: list = []

    # ── 1. Header ─────────────────────────────────────────────────────────────
    header_data = [[
        _p("AC/RC DRILL DAILY OPERATOR REPORT", _TITLE_ST),
        _p("▲  OREZONE", _ORE_ST),
    ]]
    header_tbl = Table(header_data, colWidths=[W * 0.6, W * 0.4])
    header_tbl.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW",   (0, 0), (-1, 0), 1, _NAVY),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── 2. Shift + meta row ───────────────────────────────────────────────────
    shift = report.get("shift") or "DAY"
    shift_data = [[
        _p("SHIFT:", _LABEL_ST), _p(shift, _VAL_ST), "",
        _p("Date:", _LABEL_ST),
        _p(report.get("report_date", ""), _VAL_ST),
        _p("Rig Type / Number:", _LABEL_ST),
        _p(f"{report.get('rig_type', '')}  {report.get('rig_number', '')}".strip(), _VAL_ST),
        _p("Contract Location:", _LABEL_ST),
        _p(report.get("contract_location", ""), _VAL_ST),
    ]]
    shift_cw = [12*mm, 18*mm, 4*mm, 10*mm, 26*mm, 34*mm, 22*mm, 34*mm, W - 160*mm]
    shift_tbl = Table(shift_data, colWidths=shift_cw)
    shift_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("BOX",           (1, 0), (1, 0), 0.5, _BLACK),
    ]))
    story.append(shift_tbl)
    story.append(Spacer(1, 2 * mm))

    # Hole + Angle + Client
    meta_data = [[
        _p("Hole Number:", _LABEL_ST),
        _p(report.get("hole_number", ""), _VAL_ST),
        _p("Angle:", _LABEL_ST),
        _p(_fmt(report.get("angle"), "°"), _VAL_ST),
        _p("Client:", _LABEL_ST),
        _p(report.get("client", ""), _VAL_ST),
    ]]
    meta_cw = [24*mm, 36*mm, 14*mm, 20*mm, 14*mm, W - 108*mm]
    meta_tbl = Table(meta_data, colWidths=meta_cw)
    meta_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LINEBELOW",     (1, 0), (1, 0), 0.5, _BLACK),
        ("LINEBELOW",     (3, 0), (3, 0), 0.5, _BLACK),
        ("LINEBELOW",     (5, 0), (5, 0), 0.5, _BLACK),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 3 * mm))

    # ── 3. Main drilling table ────────────────────────────────────────────────
    # Column widths: FROM | TO | RUN | ADVANCE | B/H NUMBER | TIME | COMMENTS
    c_from  = 16 * mm
    c_to    = 16 * mm
    c_run   = 16 * mm
    c_adv   = 18 * mm
    c_bh    = 32 * mm
    c_time  = 18 * mm
    c_comm  = W - (c_from + c_to + c_run + c_adv + c_bh + c_time)

    # Header: two-level (DEPTH spans FROM/TO/RUN)
    tbl_header1 = [
        _p("DEPTH", _HEAD_ST), "", "",
        _p("ADVANCE", _HEAD_ST),
        _p("B/H\nNUMBER", _HEAD_ST),
        _p("TIME", _HEAD_ST),
        _p("COMMENTS / SPECIAL\nCONDITIONS", _HEAD_ST),
    ]
    tbl_header2 = [
        _p("FROM", _HEAD_ST),
        _p("TO", _HEAD_ST),
        _p("RUN", _HEAD_ST),
        "", "", "", "",
    ]

    entries = report.get("entries") or []
    MAX_LOG_ROWS = max(len(entries), 14)  # at least 14 blank rows like the paper form

    log_data = [tbl_header1, tbl_header2]
    for i in range(MAX_LOG_ROWS):
        if i < len(entries):
            e = entries[i]
            row = [
                _p(_fmt(e.get("depth_from")), _CELL_ST),
                _p(_fmt(e.get("depth_to")),   _CELL_ST),
                _p(_fmt(e.get("run")),         _CELL_ST),
                _p(_fmt(e.get("advance")),     _CELL_ST),
                _p(str(e.get("bh_number") or ""), _CELL_ST),
                _p(_fmt(e.get("time_hours")),  _CELL_ST),
                _p(str(e.get("comments") or ""), _CELL_ST),
            ]
        else:
            row = ["", "", "", "", "", "", ""]
        log_data.append(row)

    # Total advance row (circled style replaced by bold bordered cell)
    total_adv = report.get("total_advance") or 0
    log_data.append([
        _p("TOTAL", _LABEL_ST), "",
        _p(f"{total_adv} m", ParagraphStyle("tot", fontName="Helvetica-Bold", fontSize=11, textColor=_NAVY)),
        "", "", "", "",
    ])

    cw_log = [c_from, c_to, c_run, c_adv, c_bh, c_time, c_comm]
    log_tbl = Table(log_data, colWidths=cw_log, repeatRows=2)
    row_h = 6.5 * mm
    row_heights = [7 * mm, 5.5 * mm] + [row_h] * MAX_LOG_ROWS + [8 * mm]

    log_style = TableStyle([
        # Global
        ("FONTNAME",       (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",       (0, 0), (-1, -1), 8),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",           (0, 0), (-1, -1), 0.4, _MGREY),
        ("BOX",            (0, 0), (-1, -1), 0.8, _BLACK),
        # Header row 1
        ("BACKGROUND",     (0, 0), (-1, 0), _NAVY),
        ("TEXTCOLOR",      (0, 0), (-1, 0), _WHITE),
        ("SPAN",           (0, 0), (2, 0), ),  # DEPTH span
        ("ALIGN",          (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        # Header row 2
        ("BACKGROUND",     (0, 1), (-1, 1), _NAVY),
        ("TEXTCOLOR",      (0, 1), (-1, 1), _WHITE),
        ("ALIGN",          (0, 1), (-1, 1), "CENTER"),
        ("FONTNAME",       (0, 1), (-1, 1), "Helvetica-Bold"),
        # Data rows alternate
        ("ROWBACKGROUNDS", (0, 2), (-1, -2), [_WHITE, _LGREY]),
        # Total row
        ("BACKGROUND",     (0, -1), (-1, -1), _LGREY),
        ("SPAN",           (0, -1), (1, -1)),
        ("SPAN",           (2, -1), (3, -1)),
        ("FONTNAME",       (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BOX",            (2, -1), (3, -1), 1.5, _NAVY),
        ("TOPPADDING",     (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 2),
        ("LEFTPADDING",    (0, 0), (-1, -1), 3),
    ])
    log_tbl.setStyle(log_style)
    story.append(log_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── 4. Diesel Re-Fueling ──────────────────────────────────────────────────
    equipment_list = _get_equipment_for_pdf()
    diesel = report.get("diesel") or {}

    diesel_header = [[_p("DIESEL RE-FUELING", _SEC_ST)]]
    dh_tbl = Table(diesel_header, colWidths=[W])
    dh_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
    ]))
    story.append(dh_tbl)

    c1 = W * 0.55
    c2 = W * 0.30
    c3 = W * 0.15

    diesel_rows_data = []
    for eq in equipment_list:
        code = eq.get("code", "")
        qty  = diesel.get(code, "")
        diesel_rows_data.append([
            _p(eq.get("name", ""), _CELL_ST),
            _p(str(qty) if qty else "", _CELL_ST),
            _p(eq.get("unit", "Litre"), _CELL_ST),
        ])

    # Refueler row
    refueler = report.get("refueler_name") or ""
    diesel_rows_data.append([
        _p(f"RE-FUELER Name:  {refueler}", _LABEL_ST),
        _p("Signature", _LABEL_ST),
        "",
    ])

    d_tbl = Table(diesel_rows_data, colWidths=[c1, c2, c3])
    d_tbl.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -2), 0.4, _MGREY),
        ("BOX",           (0, 0), (-1, -1), 0.8, _BLACK),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -2), [_WHITE, _LGREY]),
        ("SPAN",          (1, -1), (2, -1)),
        ("LINEABOVE",     (0, -1), (-1, -1), 0.8, _BLACK),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
    ]))
    story.append(d_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── 5. Signatures ─────────────────────────────────────────────────────────
    operator_name      = report.get("operator_name") or ""
    supervisor_name    = report.get("supervisor_name") or ""
    op_sig_b64         = report.get("operator_signature") or ""
    sup_sig_b64        = report.get("supervisor_signature") or ""

    SIG_W = W * 0.28
    SIG_H = 18 * mm

    def _sig_cell(b64: str) -> object:
        if b64:
            try:
                png_bytes = base64.b64decode(b64.encode())
                reader = ImageReader(io.BytesIO(png_bytes))
                img = RLImage(reader, width=SIG_W - 6, height=SIG_H - 4)
                return img
            except Exception:
                pass
        return _p("", _VAL_ST)

    s_cw = [38 * mm, W * 0.22, 44 * mm, W - 38*mm - W * 0.22 - 44*mm]
    sig_data = [
        [
            _p("NAME OF OPERATOR:", _LABEL_ST),
            _p(operator_name, _VAL_ST),
            _p("OPERATOR SIGNATURE:", _LABEL_ST),
            _sig_cell(op_sig_b64),
        ],
        [
            _p("NAME OF SUPERVISOR:", _LABEL_ST),
            _p(supervisor_name, _VAL_ST),
            _p("SUPERVISOR'S SIGNATURE:", _LABEL_ST),
            _sig_cell(sup_sig_b64),
        ],
    ]
    sig_tbl = Table(sig_data, colWidths=s_cw, rowHeights=[SIG_H, SIG_H])
    sig_tbl.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.5, _MGREY),
        ("BOX",           (0, 0), (-1, -1), 0.8, _BLACK),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("LINEBELOW",     (1, 0), (1, 0), 0.8, _BLACK),
        ("LINEBELOW",     (3, 0), (3, 0), 0.8, _BLACK),
        ("LINEBELOW",     (1, 1), (1, 1), 0.8, _BLACK),
        ("LINEBELOW",     (3, 1), (3, 1), 0.8, _BLACK),
    ]))
    story.append(sig_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── 6. Footer ─────────────────────────────────────────────────────────────
    validated_at = (report.get("validated_at") or "")[:10] or "—"
    foot_data = [[
        _p("Rev No", _FOOT_ST),
        _p("05", _FOOT_ST),
        _p("Doc No: OPZ/SHEQ/DC1.08", _FOOT_ST),
        _p("Approved by:", _FOOT_ST),
        _p("SHEQ Manager", _FOOT_ST),
        _p(f"Date: {validated_at}", _FOOT_ST),
        _p("Page 1 of 1", _FOOT_ST),
    ]]
    f_cw = [14*mm, 10*mm, 52*mm, 24*mm, 30*mm, 28*mm, W - 158*mm]
    foot_tbl = Table(foot_data, colWidths=f_cw)
    foot_tbl.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 7),
        ("GRID",          (0, 0), (-1, -1), 0.4, _MGREY),
        ("BOX",           (0, 0), (-1, -1), 0.8, _BLACK),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("TEXTCOLOR",     (0, 0), (-1, -1), _DGREY),
    ]))
    story.append(foot_tbl)

    doc.build(story)
    return buf.getvalue()


def _get_equipment_for_pdf() -> list[dict]:
    try:
        from app.services.drilling_service import list_equipment
        return list_equipment(active_only=True)
    except Exception:
        return [
            {"name": "RIG – SDMA 01",             "code": "SDMA01", "unit": "Litre"},
            {"name": "COMPRESSOR – SDMC 01",       "code": "SDMC01", "unit": "Litre"},
            {"name": "MOROOKA – OZMD 05",          "code": "OZMD05", "unit": "Litre"},
            {"name": "MOROOKA (CRANE) – OZMD 06",  "code": "OZMD06", "unit": "Litre"},
        ]
