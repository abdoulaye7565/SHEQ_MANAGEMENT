from __future__ import annotations

import html
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

OREZONE_HEADER_NOTE = "Industrial QHSE management document | Controlled export"
SIGNATURE_LABELS = ["Prepared by", "Checked by", "Approved by"]


def write_simple_xlsx(path: Path, sheet_name: str, headers: list[str], rows: list[list[Any]]) -> None:
    write_styled_xlsx(path, sheet_name, headers, rows)


def write_monthly_timesheet_report_xlsx(
    path: Path,
    timesheet: dict[str, Any],
    expatriates: dict[str, Any],
    generated_at: str,
) -> None:
    """Write the professional four-sheet TimeSheet 1-25 report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sheets = [
        ("Dashboard Executif", _monthly_dashboard_sheet_xml(timesheet, expatriates, generated_at)),
        ("TimeSheet 1-25", _monthly_matrix_sheet_xml(timesheet, expatriates)),
        ("Analyse Employes", _monthly_employee_analysis_sheet_xml(timesheet)),
        ("Controle Signatures", _monthly_control_sheet_xml(timesheet, expatriates, generated_at)),
    ]
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets>'
        + "".join(
            f'<sheet name="{html.escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
            for index, (name, _) in enumerate(sheets, start=1)
        )
        + "</sheets></workbook>"
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
            for index in range(1, len(sheets) + 1)
        )
        + f'<Relationship Id="rId{len(sheets) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/></Relationships>'
    )
    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index in range(1, len(sheets) + 1)
        )
        + '<Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>'
        + '<Override PartName="/xl/charts/chart1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>'
        + "</Types>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/styles.xml", _daily_lineup_styles_xml())
        for index, (_, xml) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", xml)
        archive.writestr("xl/worksheets/_rels/sheet1.xml.rels", _monthly_dashboard_sheet_rels_xml())
        archive.writestr("xl/drawings/drawing1.xml", _monthly_dashboard_drawing_xml())
        archive.writestr("xl/drawings/_rels/drawing1.xml.rels", _monthly_dashboard_drawing_rels_xml())
        archive.writestr("xl/charts/chart1.xml", _monthly_dashboard_trend_chart_xml(timesheet, expatriates))


def write_timesheet_21_20_report_xlsx(path: Path, timesheet: dict[str, Any], generated_at: str) -> None:
    """Write the professional four-sheet TimeSheet 21-20 report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sheets = [
        ("Dashboard Executif", _timesheet_21_dashboard_sheet_xml(timesheet, generated_at)),
        ("TimeSheet 21-20", _timesheet_21_matrix_sheet_xml(timesheet)),
        ("Analyse Complete", _timesheet_21_analysis_sheet_xml(timesheet)),
        ("Controle Signatures", _timesheet_21_control_sheet_xml(timesheet, generated_at)),
    ]
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
        + "".join(
            f'<sheet name="{html.escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
            for index, (name, _) in enumerate(sheets, start=1)
        )
        + "</sheets></workbook>"
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
            for index in range(1, 5)
        )
        + '<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        + "</Relationships>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index in range(1, 5)
        )
        + '<Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>'
        + '<Override PartName="/xl/charts/chart1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>'
        + "</Types>"
    )
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/styles.xml", _daily_lineup_styles_xml())
        for index, (_, xml) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", xml)
        archive.writestr("xl/worksheets/_rels/sheet1.xml.rels", _monthly_dashboard_sheet_rels_xml())
        archive.writestr("xl/drawings/drawing1.xml", _monthly_dashboard_drawing_xml())
        archive.writestr("xl/drawings/_rels/drawing1.xml.rels", _monthly_dashboard_drawing_rels_xml())
        archive.writestr("xl/charts/chart1.xml", _timesheet_21_trend_chart_xml(timesheet))


def write_styled_xlsx(
    path: Path,
    sheet_name: str,
    headers: list[str],
    rows: list[list[Any]],
    styles: list[list[str | None]] | None = None,
    include_company_description: bool = False,
    document_title: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet_xml = _worksheet_xml(headers, rows, styles, include_company_description, document_title or sheet_name)
    workbook_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="{html.escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="3"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font><font><sz val="11"/><name val="Calibri"/><color rgb="FF172033"/></font></fonts>
  <fills count="12"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF2563EB"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF22C55E"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFBBF24"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFDC2626"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF5B3DB6"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF00A6D6"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFFFFF"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFC0392B"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFF4A261"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFE5E7EB"/><bgColor indexed="64"/></patternFill></fill></fills>
  <borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFCBD5E1"/></left><right style="thin"><color rgb="FFCBD5E1"/></right><top style="thin"><color rgb="FFCBD5E1"/></top><bottom style="thin"><color rgb="FFCBD5E1"/></bottom><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="13"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="1" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="1" fillId="6" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="7" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="8" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="1" fillId="9" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="1" fillId="10" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="11" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" textRotation="45"/></xf></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""
    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/styles.xml", styles_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def _monthly_dashboard_sheet_xml(timesheet: dict[str, Any], expatriates: dict[str, Any], generated_at: str) -> str:
    summary = _monthly_combined_summary(timesheet, expatriates)
    attendance_states = max(int(summary.get("worked_days") or 0) + int(summary.get("absent_days") or 0), 1)
    presence_rate = round(int(summary.get("worked_days") or 0) * 100 / attendance_states)
    absence_rate = round(int(summary.get("absent_days") or 0) * 100 / attendance_states)
    top_hours = sorted(timesheet["rows"], key=lambda row: int(row.get("hours") or 0), reverse=True)[:5]
    site = (timesheet.get("site") or {}).get("nom") or "Tous les sites"
    rows = [
        _xml_sparse_row(1, [(1, "OREZONE\nQHSE", 16), (4, "1. DASHBOARD EXECUTIF", 1), (13, f"Site: {site}", 6)], height=28),
        _xml_sparse_row(2, [(4, "MONTHLY TIMESHEET REPORT 1-25", 17), (13, f"Period: {timesheet['period']['start']} TO {timesheet['period']['end']}", 6)], height=30),
        _xml_sparse_row(3, [(4, "TABLEAU DE BORD - SYNTHESE GLOBALE", 3), (13, f"Current month: {timesheet['period']['month']}", 6)]),
        _xml_sparse_row(4, [(13, f"Exporte le: {generated_at}", 6)]),
        _xml_sparse_row(5, [(13, "Statut: APPROVED", 12)]),
        _xml_sparse_row(7, [(1, "INDICATEURS CLES (KPI)", 1)]),
        _xml_sparse_row(8, [(1, "EMPLOYES ACTIFS", 12), (4, "HEURES TOTALES", 12), (7, "JOURS TRAVAILLES", 12), (10, "BREAK NORMAL", 14), (13, "REPOS DIMANCHE", 18)]),
        _xml_sparse_row(9, [(1, summary.get("employees", 0), 12), (4, f"{summary.get('hours', 0)} h", 12), (7, summary.get("worked_days", 0), 12), (10, summary.get("normal_break_days", 0), 14), (13, summary.get("rest_days", 0), 18)], height=30),
        _xml_sparse_row(11, [(1, "ANNUAL LEAVE", 18), (4, "PERMISSIONS", 14), (7, "SICK", 15), (10, "ABSENTS", 15), (13, "NON RENSEIGNES", 19)]),
        _xml_sparse_row(12, [(1, summary.get("annual_break_days", 0), 18), (4, summary.get("permission_days", 0), 14), (7, summary.get("sick_days", 0), 15), (10, summary.get("absent_days", 0), 15), (13, summary.get("unfilled_days", 0), 19)], height=30),
        _xml_sparse_row(14, [(1, "TAUX DE PRESENCE", 1), (5, "TAUX D'ABSENCE", 1), (9, "REPARTITION DES STATUTS", 1)]),
        _xml_sparse_row(15, [(1, f"{presence_rate}%", 12), (5, f"{absence_rate}%", 15), (9, f"Travail (10h): {summary.get('worked_days', 0)}", 12), (12, f"Break (B): {summary.get('normal_break_days', 0)}", 14)], height=30),
        _xml_sparse_row(16, [(1, "Excellent | Objectif >= 90%", 6), (5, "A surveiller | Objectif < 10%", 6), (9, f"Repos (R): {summary.get('rest_days', 0)}", 18), (12, f"Leave (AL): {summary.get('annual_break_days', 0)}", 18)]),
        _xml_sparse_row(18, [(1, "TOP 5 EMPLOYES PAR HEURES TRAVAILLEES", 1), (9, "ANALYSES RAPIDES", 1)]),
    ]
    quick_analysis = [
        f"Employes sans badge: {sum(1 for row in timesheet['rows'] if not row['employee'].get('numero_badge'))}",
        f"Jours non renseignes: {summary.get('unfilled_days', 0)}",
        f"Absences: {summary.get('absent_days', 0)}",
        f"Expatries reserves: {len(expatriates.get('rows') or [])}",
        "Document controle: APPROVED",
    ]
    for index in range(5):
        employee_row = top_hours[index] if index < len(top_hours) else None
        rows.append(
            _xml_sparse_row(
                20 + index,
                [
                    (1, _monthly_employee_name(employee_row["employee"]) if employee_row else "-", 6),
                    (5, employee_row.get("hours", 0) if employee_row else 0, 12),
                    (9, quick_analysis[index], 6),
                ],
            )
        )
    rows.extend(
        [
            _xml_sparse_row(26, [(1, "LEGENDE DES CODES", 1)]),
            _xml_sparse_row(27, [(1, "10h | Jour travaille", 12), (3, "R | Repos", 18), (5, "B | Break", 14), (7, "AL | Annual Leave", 18), (9, "P | Permission", 14), (11, "S | Sick", 15), (13, "A | Absent", 15), (15, "NR | Non renseigne", 19)]),
            _xml_sparse_row(29, [(1, "EXPATRIES - RESERVE", 1)]),
            *[
                _xml_sparse_row(30 + index, [(1, _monthly_employee_name(row["employee"]), 6)])
                for index, row in enumerate(expatriates.get("rows") or [])
            ],
        ]
    )
    merges = [
        "A1:C5", "D1:L1", "D2:L2", "D3:L3", "M1:P1", "M2:P2", "M3:P3", "M4:P4", "M5:P5",
        "A7:P7", "A8:C8", "D8:F8", "G8:I8", "J8:L8", "M8:P8",
        "A9:C9", "D9:F9", "G9:I9", "J9:L9", "M9:P9",
        "A11:C11", "D11:F11", "G11:I11", "J11:L11", "M11:P11",
        "A12:C12", "D12:F12", "G12:I12", "J12:L12", "M12:P12",
        "A14:D14", "E14:H14", "I14:P14", "A15:D15", "E15:H15", "A16:D16", "E16:H16",
        "I15:K15", "L15:P15", "I16:K16", "L16:P16", "A18:H18", "I18:P18",
        *[f"A{row}:D{row}" for row in range(20, 25)],
        *[f"E{row}:H{row}" for row in range(20, 25)],
        *[f"I{row}:P{row}" for row in range(20, 25)],
        "A26:P26", "A27:B27", "C27:D27", "E27:F27", "G27:H27", "I27:J27", "K27:L27", "M27:N27", "O27:P27",
        "A29:P29",
    ]
    return _monthly_sheet_document(
        rows,
        16,
        max(31, 30 + len(expatriates.get("rows") or [])),
        widths=[(1, 1, 12), (2, 2, 6.5), (3, 16, 12)],
        landscape=True,
        merge_refs=merges,
        print_area=f"A1:P{max(31, 30 + len(expatriates.get('rows') or []))}",
        drawing_rel_id="rId1",
    )


def _monthly_matrix_sheet_xml(timesheet: dict[str, Any], expatriates: dict[str, Any]) -> str:
    headers = ["#", "EMPLOYE", "BADGE", "FONCTION", "SITE", *[f"{day['day']} {day['weekday']}" for day in timesheet["days"]], "JT", "R", "B", "P", "S", "AL", "A", "NR", "HEURES"]
    all_rows = list(timesheet["rows"]) + list(expatriates.get("rows") or [])
    rows = [
        _xml_sparse_row(1, [(1, "OREZONE QHSE", 16), (6, "2. TIMESHEET 1-25", 1)], height=34),
        _xml_sparse_row(2, [(1, "MONTHLY TIMESHEET 1-25", 2), (32, f"Site: {(timesheet.get('site') or {}).get('nom') or 'Tous'}", 6)]),
        _xml_sparse_row(3, [(1, f"PERIODE DU {timesheet['period']['start']} AU {timesheet['period']['end']}", 3)]),
        _xml_sparse_row(5, [(1, "LEGENDE DES CODES | 10h Travail | B Break | R Repos | AL Annual Leave | P Permission | S Sick | A Absent | NR Non renseigne | N/A Hors site", 6)]),
        _xml_row(7, [(header, 20 if 5 <= position < 30 else 1) for position, header in enumerate(headers)], height=54),
    ]
    for index, row in enumerate(all_rows, start=1):
        values = [
            index,
            _monthly_employee_name(row["employee"]),
            row["employee"].get("numero_badge") or "-",
            row["employee"].get("fonction") or "-",
            row["employee"].get("site") or "-",
            *[cell["label"] for cell in row["cells"]],
            row["worked_days"], row["rest_days"], row["normal_break_days"], row.get("permission_days", 0),
            row.get("sick_days", 0), row["annual_break_days"], row.get("absent_days", 0),
            row.get("unfilled_days", 0), row["hours"],
        ]
        style_values = [(value, _monthly_status_style_id(value) if 5 <= position < 30 else 6) for position, value in enumerate(values)]
        rows.append(_xml_row(7 + index, style_values, height=24))
    total_row = 9 + len(all_rows)
    summary = _monthly_combined_summary(timesheet, expatriates)
    rows.append(
        _xml_sparse_row(
            total_row,
            [
                (1, "RECAPITULATIF GENERAL", 1),
                (31, summary["worked_days"], 12),
                (32, summary["rest_days"], 18),
                (33, summary["normal_break_days"], 14),
                (34, summary["permission_days"], 14),
                (35, summary["sick_days"], 15),
                (36, summary["annual_break_days"], 18),
                (37, summary["absent_days"], 15),
                (38, summary["unfilled_days"], 19),
                (39, summary["hours"], 12),
            ],
        )
    )
    rows.append(_xml_sparse_row(total_row + 2, [(1, "NOTES:", 1)]))
    rows.extend(_signature_rows(total_row + 5, 39))
    widths = [(1, 1, 5), (2, 2, 24), (3, 3, 12), (4, 4, 24), (5, 5, 14), (6, 30, 6.5), (31, 39, 8)]
    merges = [
        "A1:E1", "F1:AE1", "A2:AE2", "A3:AE3", "AF2:AM2", "A5:AM5",
        f"A{total_row}:AD{total_row}", f"A{total_row + 2}:AM{total_row + 4}",
        f"A{total_row + 5}:C{total_row + 5}", f"D{total_row + 5}:G{total_row + 5}", f"H{total_row + 5}:AM{total_row + 5}",
        f"A{total_row + 6}:C{total_row + 6}", f"D{total_row + 6}:G{total_row + 6}", f"H{total_row + 6}:AM{total_row + 6}",
    ]
    return _monthly_sheet_document(
        rows,
        39,
        total_row + 6,
        widths=widths,
        freeze_row=7,
        landscape=True,
        filter_ref=f"A7:AM{7 + len(all_rows)}",
        merge_refs=merges,
        print_area=f"A1:AM{total_row + 6}",
    )


def _monthly_employee_analysis_sheet_xml(timesheet: dict[str, Any]) -> str:
    ordered = sorted(timesheet["rows"], key=lambda row: int(row.get("hours") or 0), reverse=True)
    headers = ["#", "EMPLOYE", "BADGE", "FONCTION", "SITE", "JT", "R", "B", "AL", "P", "S", "A", "NR", "HEURES", "TAUX PRESENCE", "STATUT ANALYSE"]
    rows = [
        _xml_sparse_row(1, [(1, "OREZONE QHSE", 16), (5, "3. ANALYSE EMPLOYES", 1)], height=34),
        _xml_sparse_row(2, [(1, "ANALYSE DETAILLEE PAR EMPLOYE - SYNTHESE & PERFORMANCE", 2)]),
        _xml_row(5, [(header, 1) for header in headers], height=32),
    ]
    for index, row in enumerate(ordered, start=1):
        possible = max(row["worked_days"] + row.get("absent_days", 0), 1)
        rate = round(row["worked_days"] * 100 / possible)
        analysis = "Excellent" if rate >= 90 else "Bon" if rate >= 80 else "A verifier"
        style = 12 if rate >= 90 else 14 if rate >= 80 else 15
        values = [
            index, _monthly_employee_name(row["employee"]), row["employee"].get("numero_badge") or "-",
            row["employee"].get("fonction") or "-", row["employee"].get("site") or "-", row["worked_days"],
            row["rest_days"], row["normal_break_days"], row["annual_break_days"], row.get("permission_days", 0),
            row.get("sick_days", 0), row.get("absent_days", 0), row.get("unfilled_days", 0), row["hours"],
            f"{rate}%", analysis,
        ]
        rows.append(_xml_row(5 + index, [(value, style if position >= 14 else 6) for position, value in enumerate(values)], height=24))
    footer = 7 + len(ordered)
    rows.extend([
        _xml_sparse_row(footer, [(1, "TOP PRESENCE", 1), (6, "TOP ABSENCES", 1), (11, "TOP HEURES", 1)]),
        _xml_sparse_row(footer + 1, [(1, _monthly_employee_name(ordered[0]["employee"]) if ordered else "-", 6), (11, f"{ordered[0]['hours']} h" if ordered else "-", 12)]),
    ])
    merges = ["A1:D1", "E1:P1", "A2:P2", f"A{footer}:E{footer}", f"F{footer}:J{footer}", f"K{footer}:P{footer}"]
    return _monthly_sheet_document(
        rows,
        16,
        footer + 2,
        widths=[(1, 1, 5), (2, 2, 24), (3, 5, 16), (6, 16, 11)],
        freeze_row=5,
        landscape=True,
        filter_ref=f"A5:P{5 + len(ordered)}",
        merge_refs=merges,
        print_area=f"A1:P{footer + 2}",
    )


def _monthly_control_sheet_xml(timesheet: dict[str, Any], expatriates: dict[str, Any], generated_at: str) -> str:
    summary = _monthly_combined_summary(timesheet, expatriates)
    site = (timesheet.get("site") or {}).get("nom") or "Tous les sites"
    rows = [
        _xml_sparse_row(1, [(1, "OREZONE QHSE", 16), (5, "4. CONTROLE & SIGNATURES", 1)], height=34),
        _xml_sparse_row(3, [(1, "INFORMATIONS DOCUMENT", 1), (7, "CONTROLES QUALITE", 1), (12, "RESUME EXECUTIF", 1)]),
        _xml_sparse_row(4, [(1, "Document: MONTHLY TIMESHEET 1-25", 6), (7, f"Nombre d'employes: {summary.get('employees', 0)}", 6), (12, f"Total heures: {summary.get('hours', 0)} h", 6)]),
        _xml_sparse_row(5, [(1, f"Code: TS-{timesheet['period']['month']}", 6), (7, f"Nombre total lignes: {summary.get('employees', 0)}", 6), (12, "Taux de presence calcule", 6)]),
        _xml_sparse_row(6, [(1, f"Periode: {timesheet['period']['start']} TO {timesheet['period']['end']}", 6), (7, f"Jours non renseignes: {summary.get('unfilled_days', 0)}", 6), (12, f"Break normal: {summary.get('normal_break_days', 0)}", 6)]),
        _xml_sparse_row(7, [(1, f"Site: {site}", 6), (7, f"Employes sans badge: {sum(1 for row in [*timesheet['rows'], *(expatriates.get('rows') or [])] if not row['employee'].get('numero_badge'))}", 6), (12, f"Absents: {summary.get('absent_days', 0)}", 6)]),
        _xml_sparse_row(8, [(1, f"Date export: {generated_at}", 6), (7, "Heures incoherentes: 0", 6), (12, f"Annual leave: {summary.get('annual_break_days', 0)}", 6)]),
        _xml_sparse_row(10, [(1, "PREPARED BY", 9), (6, "CHECKED BY", 9), (11, "APPROVED BY", 9)]),
        _xml_sparse_row(11, [(1, "Nom:", 10), (6, "Nom:", 10), (11, "Nom:", 10)], height=30),
        _xml_sparse_row(12, [(1, "Fonction:", 10), (6, "Fonction:", 10), (11, "Fonction:", 10)], height=30),
        _xml_sparse_row(13, [(1, "Date:", 10), (6, "Date:", 10), (11, "Date:", 10)], height=30),
        _xml_sparse_row(14, [(1, "Signature:", 10), (6, "Signature:", 10), (11, "Signature:", 10)], height=42),
        _xml_sparse_row(16, [(1, "Ce document est genere automatiquement par le systeme OREZONE QHSE.", 1)]),
    ]
    merges = [
        "A1:D1", "E1:P1", "A3:F3", "G3:K3", "L3:P3",
        *[f"A{row}:F{row}" for row in range(4, 9)],
        *[f"G{row}:K{row}" for row in range(4, 9)],
        *[f"L{row}:P{row}" for row in range(4, 9)],
        "A10:E10", "F10:J10", "K10:P10",
        *[f"A{row}:E{row}" for row in range(11, 15)],
        *[f"F{row}:J{row}" for row in range(11, 15)],
        *[f"K{row}:P{row}" for row in range(11, 15)],
        "A16:P16",
    ]
    return _monthly_sheet_document(
        rows,
        16,
        17,
        widths=[(1, 16, 14)],
        landscape=True,
        merge_refs=merges,
        print_area="A1:P17",
    )


def _monthly_sheet_document(
    rows: list[str],
    col_count: int,
    last_row: int,
    *,
    widths: list[tuple[int, int, float]],
    freeze_row: int | None = None,
    landscape: bool = False,
    filter_ref: str | None = None,
    merge_refs: list[str] | None = None,
    print_area: str | None = None,
    drawing_rel_id: str | None = None,
) -> str:
    pane = f'<pane ySplit="{freeze_row}" topLeftCell="A{freeze_row + 1}" activePane="bottomLeft" state="frozen"/>' if freeze_row else ""
    cols = "<cols>" + "".join(f'<col min="{start}" max="{end}" width="{width}" customWidth="1"/>' for start, end, width in widths) + "</cols>"
    auto_filter = f'<autoFilter ref="{filter_ref}"/>' if filter_ref else ""
    merge_cells = ""
    if merge_refs:
        merge_cells = (
            f'<mergeCells count="{len(merge_refs)}">'
            + "".join(f'<mergeCell ref="{ref}"/>' for ref in merge_refs)
            + "</mergeCells>"
        )
    print_options = '<printOptions horizontalCentered="1" verticalCentered="0"/>'
    page_properties = '<pageSetUpPr fitToPage="1"/>'
    page_setup = '<pageSetup orientation="landscape" paperSize="9" fitToWidth="1" fitToHeight="0"/>' if landscape else '<pageSetup orientation="portrait" paperSize="9" fitToWidth="1" fitToHeight="1"/>'
    drawing = f'<drawing r:id="{drawing_rel_id}"/>' if drawing_rel_id else ""
    relationships_namespace = ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"' if drawing_rel_id else ""
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"{relationships_namespace}>
  <sheetPr>{page_properties}</sheetPr>
  <dimension ref="A1:{_column_name(col_count)}{last_row}"/>
  <sheetViews><sheetView workbookViewId="0" showGridLines="0">{pane}</sheetView></sheetViews>
  {cols}
  <sheetData>{"".join(rows)}</sheetData>
  {auto_filter}
  {merge_cells}
  {print_options}
  <pageMargins left="0.25" right="0.25" top="0.35" bottom="0.35" header="0.2" footer="0.2"/>
  {page_setup}
  {drawing}
</worksheet>"""


def _monthly_employee_name(employee: dict[str, Any]) -> str:
    return f"{employee.get('nom') or employee.get('nom_complet') or '-'} {employee.get('prenom') or ''}".strip()


def _monthly_combined_summary(timesheet: dict[str, Any], expatriates: dict[str, Any]) -> dict[str, int]:
    keys = (
        "employees",
        "worked_days",
        "rest_days",
        "normal_break_days",
        "permission_days",
        "sick_days",
        "annual_break_days",
        "absent_days",
        "unfilled_days",
        "hours",
    )
    national = timesheet.get("summary") or {}
    expat = expatriates.get("summary") or {}
    return {key: int(national.get(key) or 0) + int(expat.get(key) or 0) for key in keys}


def _monthly_status_style(value: Any) -> str | None:
    return {
        "10h": "done",
        "8H": "holiday",
        "R": "rest",
        "B": "break",
        "P": "permission",
        "S": "sick",
        "A": "danger",
        "AL": "annual",
        "NR": "unfilled",
        "N/A": "unfilled",
    }.get(str(value or ""))


def _monthly_status_style_id(value: Any) -> int:
    """Use the vivid report palette instead of the generic workbook styles."""
    return {
        "10h": 12,
        "12h": 13,
        "8H": 13,
        "R": 11,
        "B": 14,
        "P": 19,
        "S": 15,
        "A": 15,
        "AL": 18,
        "NR": 11,
        "N/A": 11,
    }.get(str(value or ""), 10)


def _timesheet_21_dashboard_sheet_xml(timesheet: dict[str, Any], generated_at: str) -> str:
    summary = timesheet["summary"]
    validation = timesheet.get("validation") or {"issues": []}
    sync = timesheet.get("synchronization") or {}
    attendance_states = max(int(summary.get("worked_days") or 0) + int(summary.get("absent_days") or 0), 1)
    presence_rate = round(int(summary.get("worked_days") or 0) * 100 / attendance_states)
    actual = float(summary.get("actual_hours") or 0)
    planned = float(summary.get("hours") or 0)
    variance = round(actual - planned, 2)
    site = (timesheet.get("site") or {}).get("nom") or "Tous les sites"
    top_hours = sorted(timesheet.get("rows") or [], key=lambda row: float(row.get("hours") or 0), reverse=True)[:5]
    rows = [
        _xml_sparse_row(1, [(1, "OREZONE\nQHSE", 16), (4, "1. DASHBOARD EXECUTIF", 1), (13, f"Site: {site}", 6)], height=28),
        _xml_sparse_row(2, [(4, "MONTHLY TIMESHEET REPORT 21-20", 17), (13, f"Period: {timesheet['period']['start']} TO {timesheet['period']['end']}", 6)], height=30),
        _xml_sparse_row(3, [(4, "ANALYSE OPERATIONNELLE & CONTROLE DES HEURES", 3), (13, f"Exporte le: {generated_at}", 6)]),
        _xml_sparse_row(4, [(13, f"Presence synchronisee: {sync.get('days_with_data', 0)} jour(s)", 12)]),
        _xml_sparse_row(5, [(13, "Statut: APPROVED" if not validation.get("blocking") else "Statut: A CORRIGER", 12 if not validation.get("blocking") else 15)]),
        _xml_sparse_row(7, [(1, "INDICATEURS CLES (KPI)", 1)]),
        _xml_sparse_row(8, [(1, "EMPLOYES", 12), (4, "HEURES PLANIFIEES", 12), (7, "HEURES REELLES", 12), (10, "HEURES 12H", 13), (13, "HEURES 8H", 12)]),
        _xml_sparse_row(9, [(1, summary.get("employees", 0), 12), (4, f"{planned:g} h", 12), (7, f"{actual:g} h", 12), (10, f"{summary.get('drilling_hours', 0)} h", 13), (13, f"{summary.get('standard_hours', 0)} h", 12)], height=30),
        _xml_sparse_row(11, [(1, "JOURS TRAVAILLES", 12), (4, "BREAKS", 14), (7, "ABSENTS", 15), (10, "NON RENSEIGNES", 19), (13, "ANOMALIES", 15)]),
        _xml_sparse_row(12, [(1, summary.get("worked_days", 0), 12), (4, summary.get("break_days", 0), 14), (7, summary.get("absent_days", 0), 15), (10, summary.get("unfilled_days", 0), 19), (13, len(validation.get("issues") or []), 15)], height=30),
        _xml_sparse_row(14, [(1, "TAUX DE PRESENCE", 1), (5, "ECART HEURES REELLES / PLANIFIEES", 1), (9, "REPARTITION OPERATIONNELLE", 1)]),
        _xml_sparse_row(15, [(1, f"{presence_rate}%", 12 if presence_rate >= 90 else 14), (5, f"{variance:+g} h", 12 if variance >= 0 else 15), (9, f"Drilling: {summary.get('drilling_hours', 0)} h", 13), (12, f"Standard: {summary.get('standard_hours', 0)} h", 12)], height=30),
        _xml_sparse_row(16, [(1, "Objectif >= 90%", 6), (5, "Comparaison presence / planification", 6), (9, f"Repos: {summary.get('rest_days', 0)}", 11), (12, f"Permissions: {summary.get('permission_days', 0)}", 19)]),
        _xml_sparse_row(18, [(1, "TOP 5 EMPLOYES PAR HEURES", 1), (9, "COURBES DE TENDANCE", 1)]),
    ]
    for index in range(5):
        employee_row = top_hours[index] if index < len(top_hours) else None
        rows.append(
            _xml_sparse_row(
                20 + index,
                [(1, _monthly_employee_name(employee_row["employee"]) if employee_row else "-", 6), (5, employee_row.get("hours", 0) if employee_row else 0, 13)],
            )
        )
    rows.extend([
        _xml_sparse_row(26, [(1, "Legende", 1)]),
        _xml_sparse_row(27, [(1, "12 = JOURS DRILLING", 13), (3, "8 = JOURS FERIES & CHOMES PAYES", 12), (5, "R = OFF DAYS", 11), (7, "B = BREAK", 14), (9, "P = PERMISSION", 19), (11, "S = SICK LEAVE", 15), (13, "AL = ANNUAL LEAVE", 18), (15, "A = ABSENT", 15)]),
        _xml_sparse_row(29, [(1, "MLE | NOM | PRENOMS | FONCTION", 6), (9, "Prepared by | Checked by | Approved by", 6)]),
        _xml_sparse_row(30, [(1, "Jour ferie ou chome paye = 8H", 6), (9, "ANNUAL LEAVE | Document controle", 6)]),
    ])
    merges = [
        "A1:C5", "D1:L1", "D2:L2", "D3:L3", "M1:P1", "M2:P2", "M3:P3", "M4:P4", "M5:P5",
        "A7:P7", *[f"{start}{row}:{end}{row}" for row in (8, 9, 11, 12) for start, end in (("A", "C"), ("D", "F"), ("G", "I"), ("J", "L"), ("M", "P"))],
        "A14:D14", "E14:H14", "I14:P14", "A15:D15", "E15:H15", "I15:K15", "L15:P15", "A16:D16", "E16:H16", "I16:K16", "L16:P16",
        "A18:H18", "I18:P18", *[f"A{row}:D{row}" for row in range(20, 25)], *[f"E{row}:H{row}" for row in range(20, 25)],
        "A26:P26", "A27:B27", "C27:D27", "E27:F27", "G27:H27", "I27:J27", "K27:L27", "M27:N27", "O27:P27", "A29:H29", "I29:P29", "A30:H30", "I30:P30",
    ]
    return _monthly_sheet_document(rows, 16, 30, widths=[(1, 1, 12), (2, 2, 6.5), (3, 16, 12)], landscape=True, merge_refs=merges, drawing_rel_id="rId1")


def _timesheet_21_matrix_sheet_xml(timesheet: dict[str, Any]) -> str:
    headers = ["#", "MLE", "NOM", "PRENOMS", "FONCTION", *[f"{day['day']:02d} {day['weekday']}" for day in timesheet["days"]], "JT", "12H", "8H", "R", "A", "B", "P", "S", "H"]
    rows = [
        _xml_sparse_row(1, [(1, "OREZONE QHSE", 16), (6, "2. TIMESHEET 21-20", 1)], height=34),
        _xml_sparse_row(2, [(1, "MONTHLY TIMESHEET 21-20", 17), (32, f"Period: {timesheet['period']['start']} TO {timesheet['period']['end']}", 6)]),
        _xml_sparse_row(4, [(1, "Legende | 12 Drilling | 8 Standard/Ferie | R Off days | B Break | P Permission | S Sick | AL Annual Leave | A Absent | NR Non renseigne", 6)]),
        _xml_row(6, [(header, 20 if 5 <= index < 5 + len(timesheet["days"]) else 1) for index, header in enumerate(headers)], height=54),
    ]
    for index, row in enumerate(timesheet["rows"], start=1):
        employee = row["employee"]
        values = [index, employee.get("matricule") or "-", employee.get("nom") or employee.get("nom_complet") or "-", employee.get("prenom") or "", employee.get("fonction") or "-", *[_timesheet_21_cell_label(cell) for cell in row["cells"]], row["worked_days"], row.get("drilling_hours", 0), row.get("standard_hours", 0), row["rest_days"], row.get("absent_days", 0), row["break_days"], row.get("permission_days", 0), row.get("sick_days", 0), row["hours"]]
        styled = []
        for position, value in enumerate(values):
            cell_index = position - 5
            style = _timesheet_21_cell_style_id(row["cells"][cell_index]) if 0 <= cell_index < len(row["cells"]) else 6
            styled.append((value, style))
        rows.append(_xml_row(6 + index, styled, height=24))
    total_row = 8 + len(timesheet["rows"])
    summary = timesheet["summary"]
    rows.append(_xml_sparse_row(total_row, [(1, "RECAPITULATIF GENERAL", 1), (6 + len(timesheet["days"]), summary.get("worked_days", 0), 12), (7 + len(timesheet["days"]), summary.get("drilling_hours", 0), 13), (8 + len(timesheet["days"]), summary.get("standard_hours", 0), 12), (14 + len(timesheet["days"]), summary.get("hours", 0), 13)]))
    rows.extend(_signature_rows(total_row + 3, len(headers)))
    return _monthly_sheet_document(rows, len(headers), total_row + 4, widths=[(1, 1, 5), (2, 2, 12), (3, 4, 20), (5, 5, 24), (6, 5 + len(timesheet["days"]), 6.5), (6 + len(timesheet["days"]), len(headers), 8)], freeze_row=6, landscape=True, filter_ref=f"A6:{_column_name(len(headers))}{6 + len(timesheet['rows'])}")


def _timesheet_21_analysis_sheet_xml(timesheet: dict[str, Any]) -> str:
    headers = ["#", "EMPLOYE", "BADGE", "FONCTION", "SITE", "JT", "12H", "8H", "R", "B", "P", "S", "A", "NR", "PLANIFIE", "REEL", "ECART", "TAUX PRESENCE", "STATUT"]
    rows = [_xml_sparse_row(1, [(1, "OREZONE QHSE", 16), (6, "3. ANALYSE COMPLETE", 1)], height=34), _xml_sparse_row(2, [(1, "SYNTHESE DETAILLEE PAR EMPLOYE", 17)]), _xml_row(5, [(header, 1) for header in headers], height=32)]
    ordered = sorted(timesheet["rows"], key=lambda row: float(row.get("hours") or 0), reverse=True)
    for index, row in enumerate(ordered, start=1):
        employee = row["employee"]
        attendance_states = max(int(row.get("worked_days") or 0) + int(row.get("absent_days") or 0), 1)
        rate = round(int(row.get("worked_days") or 0) * 100 / attendance_states)
        variance = round(float(row.get("actual_hours") or 0) - float(row.get("hours") or 0), 2)
        status = "Conforme" if rate >= 90 and not row.get("unfilled_days") else "A verifier"
        values = [index, _monthly_employee_name(employee), employee.get("numero_badge") or "-", employee.get("fonction") or "-", employee.get("site") or "-", row["worked_days"], row["drilling_hours"], row["standard_hours"], row["rest_days"], row["break_days"], row.get("permission_days", 0), row.get("sick_days", 0), row.get("absent_days", 0), row.get("unfilled_days", 0), row["hours"], row.get("actual_hours", 0), variance, f"{rate}%", status]
        rows.append(_xml_row(5 + index, [(value, 12 if position >= 17 and status == "Conforme" else 15 if position >= 17 else 6) for position, value in enumerate(values)], height=24))
    return _monthly_sheet_document(rows, len(headers), 6 + len(ordered), widths=[(1, 1, 5), (2, 2, 24), (3, 5, 16), (6, len(headers), 11)], freeze_row=5, landscape=True, filter_ref=f"A5:{_column_name(len(headers))}{5 + len(ordered)}")


def _timesheet_21_control_sheet_xml(timesheet: dict[str, Any], generated_at: str) -> str:
    summary = timesheet["summary"]
    validation = timesheet.get("validation") or {"issues": [], "blocking": []}
    sync = timesheet.get("synchronization") or {}
    rows = [
        _xml_sparse_row(1, [(1, "OREZONE QHSE", 16), (5, "4. CONTROLE & SIGNATURES", 1)], height=34),
        _xml_sparse_row(3, [(1, "INFORMATIONS DOCUMENT", 1), (7, "CONTROLES QUALITE", 1), (12, "RESUME EXECUTIF", 1)]),
        _xml_sparse_row(4, [(1, "Document: MONTHLY TIMESHEET 21-20", 6), (7, f"Employes: {summary.get('employees', 0)}", 6), (12, f"Heures planifiees: {summary.get('hours', 0)} h", 6)]),
        _xml_sparse_row(5, [(1, f"Periode: {timesheet['period']['start']} TO {timesheet['period']['end']}", 6), (7, f"Anomalies: {len(validation.get('issues') or [])}", 6), (12, f"Heures reelles: {summary.get('actual_hours', 0)} h", 6)]),
        _xml_sparse_row(6, [(1, f"Date export: {generated_at}", 6), (7, f"Points bloquants: {len(validation.get('blocking') or [])}", 6), (12, f"Drilling: {summary.get('drilling_hours', 0)} h", 6)]),
        _xml_sparse_row(7, [(1, f"Source: {sync.get('source', 'presences')}", 6), (7, f"Jours valides: {sync.get('validated_days', 0)}", 6), (12, f"Standard: {summary.get('standard_hours', 0)} h", 6)]),
        _xml_sparse_row(9, [(1, "PREPARED BY", 9), (6, "CHECKED BY", 9), (11, "APPROVED BY", 9)]),
        _xml_sparse_row(10, [(1, "Nom / Fonction / Date / Signature", 10), (6, "Nom / Fonction / Date / Signature", 10), (11, "Nom / Fonction / Date / Signature", 10)], height=70),
        _xml_sparse_row(12, [(1, "Ce document est genere automatiquement par le systeme OREZONE QHSE.", 1)]),
    ]
    merges = ["A1:D1", "E1:P1", "A3:F3", "G3:K3", "L3:P3", *[f"A{row}:F{row}" for row in range(4, 8)], *[f"G{row}:K{row}" for row in range(4, 8)], *[f"L{row}:P{row}" for row in range(4, 8)], "A9:E9", "F9:J9", "K9:P9", "A10:E10", "F10:J10", "K10:P10", "A12:P12"]
    return _monthly_sheet_document(rows, 16, 12, widths=[(1, 16, 14)], landscape=True, merge_refs=merges)


def _timesheet_21_cell_label(cell: dict[str, Any]) -> str:
    status = str(cell.get("status") or "")
    if status in {"worked_drilling", "worked_standard"}:
        return str(int(float(cell.get("hours") or 0)))
    return str(cell.get("label") or "")


def _timesheet_21_cell_style_id(cell: dict[str, Any]) -> int:
    status = str(cell.get("status") or "")
    label = str(cell.get("label") or "")
    if status == "worked_drilling":
        return 13
    if status in {"worked_standard", "holiday"}:
        return 12
    if status == "rest" or status in {"unfilled", "not_assigned"}:
        return 11
    if status == "absent":
        return 15
    if status == "break" and label == "AL":
        return 18
    if status == "break" and label == "P":
        return 19
    if status == "break" and label == "S":
        return 15
    if status == "break":
        return 14
    return 10


def _timesheet_21_trend_chart_xml(timesheet: dict[str, Any]) -> str:
    rows = timesheet.get("rows") or []
    labels = [f"{day['day']:02d}" for day in timesheet.get("days") or []]
    hours = [sum(float(row["cells"][index].get("hours") or 0) for row in rows) for index in range(len(labels))]
    present = [sum(1 for row in rows if str(row["cells"][index].get("status") or "") in {"worked_drilling", "worked_standard", "holiday"}) for index in range(len(labels))]
    return _monthly_line_chart_xml(labels, hours, present)


def _monthly_dashboard_sheet_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/>
</Relationships>"""


def _monthly_dashboard_drawing_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" Target="../charts/chart1.xml"/>
</Relationships>"""


def _monthly_dashboard_drawing_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <xdr:twoCellAnchor>
    <xdr:from><xdr:col>8</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>17</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>
    <xdr:to><xdr:col>16</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>25</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>
    <xdr:graphicFrame macro="">
      <xdr:nvGraphicFramePr><xdr:cNvPr id="2" name="Courbes de tendance"/><xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr>
      <xdr:xfrm/>
      <a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">
        <c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" r:id="rId1"/>
      </a:graphicData></a:graphic>
    </xdr:graphicFrame>
    <xdr:clientData/>
  </xdr:twoCellAnchor>
</xdr:wsDr>"""


def _monthly_dashboard_trend_chart_xml(timesheet: dict[str, Any], expatriates: dict[str, Any]) -> str:
    all_rows = [*timesheet.get("rows", []), *(expatriates.get("rows") or [])]
    labels = [f"{day['day']:02d}" for day in timesheet.get("days", [])]
    hours = [
        sum(float(row["cells"][index].get("hours") or 0) for row in all_rows)
        for index in range(len(labels))
    ]
    present = [
        sum(1 for row in all_rows if str(row["cells"][index].get("status") or "") in {"worked", "holiday"})
        for index in range(len(labels))
    ]
    return _monthly_line_chart_xml(labels, hours, present)


def _monthly_line_chart_xml(labels: list[str], hours: list[float], present: list[int]) -> str:
    category_points = "".join(f'<c:pt idx="{index}"><c:v>{html.escape(label)}</c:v></c:pt>' for index, label in enumerate(labels))
    hours_points = "".join(f'<c:pt idx="{index}"><c:v>{value}</c:v></c:pt>' for index, value in enumerate(hours))
    present_points = "".join(f'<c:pt idx="{index}"><c:v>{value}</c:v></c:pt>' for index, value in enumerate(present))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
 <c:chart><c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="fr-FR" sz="1100" b="1"/><a:t>TENDANCE JOURNALIERE</a:t></a:r></a:p></c:rich></c:tx><c:layout/></c:title>
 <c:autoTitleDeleted val="0"/><c:plotArea><c:layout/>
 <c:lineChart><c:grouping val="standard"/><c:varyColors val="0"/>
 {_monthly_line_series_xml(0, "Heures travaillees", "2563EB", category_points, hours_points, len(labels))}
 {_monthly_line_series_xml(1, "Employes presents", "16A34A", category_points, present_points, len(labels))}
 <c:marker val="1"/><c:axId val="1376588736"/><c:axId val="1376588864"/></c:lineChart>
 <c:catAx><c:axId val="1376588736"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="b"/><c:tickLblPos val="nextTo"/><c:crossAx val="1376588864"/><c:crosses val="autoZero"/><c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/></c:catAx>
 <c:valAx><c:axId val="1376588864"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="l"/><c:majorGridlines/><c:numFmt formatCode="0" sourceLinked="1"/><c:tickLblPos val="nextTo"/><c:crossAx val="1376588736"/><c:crosses val="autoZero"/><c:crossBetween val="between"/></c:valAx>
 </c:plotArea><c:legend><c:legendPos val="b"/><c:layout/></c:legend><c:plotVisOnly val="1"/><c:dispBlanksAs val="zero"/></c:chart>
</c:chartSpace>"""


def _monthly_line_series_xml(
    index: int,
    name: str,
    color: str,
    category_points: str,
    value_points: str,
    point_count: int,
) -> str:
    return f"""<c:ser><c:idx val="{index}"/><c:order val="{index}"/><c:tx><c:v>{html.escape(name)}</c:v></c:tx>
<c:spPr><a:ln w="28575"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill></a:ln></c:spPr>
<c:marker><c:symbol val="circle"/><c:size val="5"/></c:marker>
<c:cat><c:strLit><c:ptCount val="{point_count}"/>{category_points}</c:strLit></c:cat>
<c:val><c:numLit><c:formatCode>0</c:formatCode><c:ptCount val="{point_count}"/>{value_points}</c:numLit></c:val>
</c:ser>"""


def write_daily_lineup_xlsx(
    path: Path,
    rows: list[dict[str, Any]],
    generated_at: str,
    summary: dict[str, int],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "N",
        "Matricule",
        "Nom",
        "Prenom",
        "Badge",
        "Fonction",
        "Site",
        "Shift",
        "Situation",
        "Prochain break",
        "Observation",
    ]
    data_rows = [
        [
            index,
            row.get("matricule") or "",
            row.get("nom") or row.get("nom_complet") or "",
            row.get("prenom") or "",
            row.get("numero_badge") or "",
            row.get("fonction") or "",
            row.get("site") or "",
            row.get("shift") or "",
            row.get("situation") or "",
            row.get("prochain_break") or "",
            row.get("observation") or "",
        ]
        for index, row in enumerate(rows, start=1)
    ]
    sheet_xml = _daily_lineup_worksheet_xml(headers, data_rows, generated_at, summary)
    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="OREZONE Employees" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""
    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/styles.xml", _daily_lineup_styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def write_attendance_list_xlsx(
    path: Path,
    date_presence: str,
    rows: list[dict[str, Any]],
    generated_at: str,
    summary: dict[str, int | float],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "N",
        "Nom",
        "Prenom",
        "Badge",
        "Fonction",
        "Shift",
        "Statut",
        "Entree",
        "Sortie",
        "Heures",
        "Controle",
    ]
    data_rows = _attendance_grouped_rows(rows)
    sheet_xml = _attendance_worksheet_xml(headers, data_rows, date_presence, generated_at, summary)
    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Presence" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""
    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/styles.xml", _daily_lineup_styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def write_toolbox_talk_xlsx(
    path: Path,
    month_label: str,
    month_value: str,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    generated_at: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "Date",
        "Day",
        "English Topic",
        "Theme Francais",
        "Facilitator",
        "Site",
    ]
    sheet_xml = _toolbox_talk_worksheet_xml(headers, rows, month_label, month_value, summary, generated_at)
    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Toolbox Talk" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""
    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/styles.xml", _daily_lineup_styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def write_equipment_maintenance_xlsx(
    path: Path,
    rows: list[dict[str, Any]],
    generated_at: str,
    summary: dict[str, int | float],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "Code",
        "Equipment",
        "Category",
        "Site",
        "Responsible",
        "Type",
        "Priority",
        "Status",
        "Planned date",
        "Next date",
        "Current odometer km",
        "Last maintenance km",
        "KM to add",
        "Next maintenance km",
        "Km remaining",
        "Alert",
        "Cost",
        "Observations",
    ]
    sheets = [
        ("Dashboard Executif", _equipment_maintenance_dashboard_xml(rows, generated_at, summary)),
        ("Registre Maintenance", _equipment_maintenance_worksheet_xml(headers, rows, generated_at, summary)),
        ("Analyse Couts Alertes", _equipment_maintenance_analysis_xml(rows, summary)),
        ("Controle Signatures", _equipment_maintenance_control_xml(rows, generated_at, summary)),
    ]
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
        + "".join(
            f'<sheet name="{html.escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
            for index, (name, _) in enumerate(sheets, start=1)
        )
        + "</sheets></workbook>"
    )
    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
            for index in range(1, 5)
        )
        + '<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        + "</Relationships>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index in range(1, 5)
        )
        + '<Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>'
        + '<Override PartName="/xl/charts/chart1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>'
        + "</Types>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/styles.xml", _daily_lineup_styles_xml())
        for index, (_, xml) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", xml)
        archive.writestr("xl/worksheets/_rels/sheet1.xml.rels", _monthly_dashboard_sheet_rels_xml())
        archive.writestr("xl/drawings/drawing1.xml", _monthly_dashboard_drawing_xml())
        archive.writestr("xl/drawings/_rels/drawing1.xml.rels", _monthly_dashboard_drawing_rels_xml())
        archive.writestr("xl/charts/chart1.xml", _equipment_maintenance_cost_chart_xml(rows))


def _worksheet_xml(
    headers: list[str],
    rows: list[list[Any]],
    styles: list[list[str | None]] | None = None,
    include_company_description: bool = False,
    document_title: str | None = None,
) -> str:
    header_row_index = 7
    title = document_title or "OREZONE QHSE EXPORT"
    if "RISK REGISTER" in str(title).upper():
        return _risk_register_worksheet_xml(headers, rows, styles, title)
    day_start, day_end = _timesheet_day_bounds(headers, title)
    is_timesheet = day_end >= day_start
    training_start, training_end = _training_matrix_bounds(headers, title)
    is_training_matrix = training_end >= training_start
    summary_row = ["Summary", f"Rows: {len(rows)}"]
    if "MONTHLY TIMESHEET 1-25" in str(title).upper():
        month_value, period_value = _monthly_125_title_values(title)
        summary_row = ["Current month", month_value, "Period", period_value, "Rows", len(rows)]
    all_rows = [
        ["OREZONE", "", title],
        ["", "", "Controlled QHSE document | Document QHSE controle"],
        ["", "", OREZONE_HEADER_NOTE],
        [],
        summary_row,
        [],
        headers,
        *rows,
        [],
        ["Prepared by", "", "Checked by", "", "Approved by", ""],
        ["Name / Date / Signature", "", "Name / Date / Signature", "", "Name / Date / Signature", ""],
    ]
    xml_rows = []
    for row_index, row in enumerate(all_rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{_column_name(col_index)}{row_index}"
            style_id = _style_id(row_index, col_index, styles, header_row_index, headers, title)
            style = f' s="{style_id}"' if style_id else ""
            if isinstance(value, (int, float)):
                cells.append(f'<c r="{ref}"{style}><v>{value}</v></c>')
            else:
                text = html.escape(str(value or ""))
                cells.append(f'<c r="{ref}" t="inlineStr"{style}><is><t>{text}</t></is></c>')
        header_height = is_timesheet or is_training_matrix
        height_attr = ' ht="46" customHeight="1"' if header_height and row_index == header_row_index else ""
        xml_rows.append(f'<row r="{row_index}"{height_attr}>{"".join(cells)}</row>')
    col_count = max(len(headers), 6)
    last_row = max(len(all_rows), 1)
    dimension = f"A1:{_column_name(col_count)}{last_row}"
    header_filter_ref = f"A{header_row_index}:{_column_name(len(headers))}{last_row}"
    footer_start = len(all_rows) - 1
    merge_xml = (
        '<mergeCells count="8">'
        '<mergeCell ref="A1:B3"/>'
        f'<mergeCell ref="C1:{_column_name(col_count)}1"/>'
        f'<mergeCell ref="C2:{_column_name(col_count)}2"/>'
        f'<mergeCell ref="C3:{_column_name(col_count)}3"/>'
        f'<mergeCell ref="B5:{_column_name(col_count)}5"/>'
        f'<mergeCell ref="A{footer_start}:B{footer_start}"/>'
        f'<mergeCell ref="C{footer_start}:D{footer_start}"/>'
        f'<mergeCell ref="E{footer_start}:{_column_name(col_count)}{footer_start}"/>'
        "</mergeCells>"
    )
    cols_xml = _worksheet_cols_xml(headers, title)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="{header_row_index}" topLeftCell="A{header_row_index + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  {cols_xml}
  <sheetData>{"".join(xml_rows)}</sheetData>
  <autoFilter ref="{header_filter_ref}"/>
  {merge_xml}
</worksheet>"""


def _risk_register_worksheet_xml(
    headers: list[str],
    rows: list[list[Any]],
    styles: list[list[str | None]] | None,
    document_title: str,
) -> str:
    table_start = 10
    pre_rows = rows[:4]
    pre_styles = (styles or [])[:4]
    data_rows = rows[4:]
    data_styles = (styles or [])[4:]
    col_count = max(len(headers), 21)
    table_end = table_start + len(data_rows)
    signature_start = table_end + 2
    xml_rows = [
        _xml_sparse_row(1, [(1, "OREZONE", 1), (3, document_title, 1)], height=34),
        _xml_sparse_row(2, [(3, "ISO 31000 / ISO 45001 risk register | Hazard identification, controls and residual risk tracking", 6)]),
        _xml_sparse_row(3, [(3, OREZONE_HEADER_NOTE, 11)]),
        _xml_row(5, _styled_row_values(pre_rows[0] if len(pre_rows) > 0 else [], pre_styles[0] if len(pre_styles) > 0 else [])),
        _xml_row(6, _styled_row_values(pre_rows[2] if len(pre_rows) > 2 else [], pre_styles[2] if len(pre_styles) > 2 else [])),
        _xml_sparse_row(
            8,
            [(1, "Method: initial risk = probability x severity. Apply control hierarchy, then reassess residual risk before approval.", 6)],
            height=28,
        ),
        _xml_row(table_start, [(header, 1) for header in headers], height=42),
    ]
    for offset, row in enumerate(data_rows, start=1):
        style_row = data_styles[offset - 1] if offset - 1 < len(data_styles) else []
        xml_rows.append(_xml_row(table_start + offset, _styled_row_values(row, style_row), height=36))
    xml_rows.extend(_signature_rows(signature_start, col_count))

    dimension = f"A1:{_column_name(col_count)}{signature_start + 1}"
    cols_xml = _risk_register_cols_xml()
    merge_xml = (
        '<mergeCells count="12">'
        '<mergeCell ref="A1:B3"/>'
        f'<mergeCell ref="C1:{_column_name(col_count)}1"/>'
        f'<mergeCell ref="C2:{_column_name(col_count)}2"/>'
        f'<mergeCell ref="C3:{_column_name(col_count)}3"/>'
        f'<mergeCell ref="G6:{_column_name(col_count)}6"/>'
        f'<mergeCell ref="A8:{_column_name(col_count)}8"/>'
        f'<mergeCell ref="A{signature_start}:C{signature_start}"/>'
        f'<mergeCell ref="D{signature_start}:G{signature_start}"/>'
        f'<mergeCell ref="H{signature_start}:K{signature_start}"/>'
        f'<mergeCell ref="A{signature_start + 1}:C{signature_start + 1}"/>'
        f'<mergeCell ref="D{signature_start + 1}:G{signature_start + 1}"/>'
        f'<mergeCell ref="H{signature_start + 1}:K{signature_start + 1}"/>'
        '</mergeCells>'
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="{table_start}" topLeftCell="A{table_start + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  {cols_xml}
  <sheetData>{"".join(xml_rows)}</sheetData>
  <autoFilter ref="A{table_start}:{_column_name(len(headers))}{max(table_end, table_start)}"/>
  {merge_xml}
  <pageMargins left="0.25" right="0.25" top="0.45" bottom="0.45" header="0.2" footer="0.2"/>
  <pageSetup orientation="landscape" paperSize="9" fitToWidth="1" fitToHeight="0"/>
</worksheet>"""


def _risk_register_cols_xml() -> str:
    widths = [
        (1, 1, 20),
        (2, 2, 20),
        (3, 3, 22),
        (4, 4, 30),
        (5, 6, 32),
        (7, 7, 16),
        (8, 8, 24),
        (9, 12, 11),
        (13, 13, 22),
        (14, 14, 34),
        (15, 18, 11),
        (19, 19, 17),
        (20, 21, 15),
    ]
    return "<cols>" + "".join(
        f'<col min="{start}" max="{end}" width="{width}" customWidth="1"/>'
        for start, end, width in widths
    ) + "</cols>"


def _styled_row_values(row: list[Any], style_row: list[str | None]) -> list[tuple[Any, int]]:
    return [
        (value, _style_key_to_id(style_row[index] if index < len(style_row) else None))
        for index, value in enumerate(row)
    ]


def _style_key_to_id(style_key: str | None) -> int:
    return {
        "done": 2,
        "soon": 3,
        "missing": 4,
        "expired": 4,
        "danger": 4,
        "annual": 5,
        "section": 1,
        "drilling": 7,
        "standard": 8,
        "rest": 9,
        "break": 3,
        "permission": 10,
        "sick": 2,
        "holiday": 2,
        "unfilled": 11,
    }.get(str(style_key or ""), 6)


def _worksheet_cols_xml(headers: list[str], document_title: str) -> str:
    col_count = max(len(headers), 6)
    title = str(document_title or "").upper()
    is_timesheet = "TIMESHEET" in title and len(headers) > 15
    is_training_matrix = "TRAINING MATRIX" in title and len(headers) > 4
    if is_training_matrix:
        cols = [
            '<col min="1" max="1" width="7" customWidth="1"/>',
            '<col min="2" max="2" width="28" customWidth="1"/>',
            '<col min="3" max="3" width="14" customWidth="1"/>',
            '<col min="4" max="4" width="28" customWidth="1"/>',
        ]
        if col_count >= 5:
            cols.append(f'<col min="5" max="{col_count}" width="12" customWidth="1"/>')
        return f"<cols>{''.join(cols)}</cols>"
    if not is_timesheet:
        return f'<cols><col min="1" max="{col_count}" width="20" customWidth="1"/></cols>'
    day_start, day_end = _timesheet_day_bounds(headers, title)
    totals_start = day_end + 1
    if headers[:4] == ["MLE", "NOM", "PRENOMS", "FONCTION"]:
        cols = [
            '<col min="1" max="1" width="12" customWidth="1"/>',
            '<col min="2" max="3" width="22" customWidth="1"/>',
            '<col min="4" max="4" width="30" customWidth="1"/>',
        ]
    else:
        cols = [
            '<col min="1" max="1" width="28" customWidth="1"/>',
            '<col min="2" max="2" width="14" customWidth="1"/>',
            '<col min="3" max="3" width="26" customWidth="1"/>',
            '<col min="4" max="4" width="18" customWidth="1"/>',
        ]
    if day_end >= day_start:
        cols.append(f'<col min="{day_start}" max="{day_end}" width="6.5" customWidth="1"/>')
    if totals_start <= col_count:
        cols.append(f'<col min="{totals_start}" max="{col_count}" width="9" customWidth="1"/>')
    return f"<cols>{''.join(cols)}</cols>"


def _timesheet_day_bounds(headers: list[str], document_title: str) -> tuple[int, int]:
    title = str(document_title or "").upper()
    if "TIMESHEET" not in title or len(headers) <= 15:
        return 1, 0
    day_start = 5
    total_labels = {
        "TOTAL",
        "12H",
        "8H",
        "R",
        "A",
        "B",
        "P",
        "S",
        "H",
        "Jours travailles",
        "Repos",
        "Break normal",
        "Break annuel",
        "Heures",
    }
    day_end = day_start - 1
    for index, header in enumerate(headers[day_start - 1 :], start=day_start):
        if str(header) in total_labels:
            break
        day_end = index
    return day_start, day_end


def _training_matrix_bounds(headers: list[str], document_title: str) -> tuple[int, int]:
    title = str(document_title or "").upper()
    if "TRAINING MATRIX" not in title or len(headers) <= 4:
        return 1, 0
    return 5, len(headers)


def _monthly_125_title_values(title: str) -> tuple[str, str]:
    parts = [part.strip() for part in str(title or "").split("|")]
    month = ""
    period = ""
    for part in parts:
        upper = part.upper()
        if upper.startswith("CURRENT MONTH"):
            month = part.replace("CURRENT MONTH", "", 1).strip()
        if upper.startswith("PERIOD"):
            period = part.replace("PERIOD", "", 1).strip()
    return month or "-", period or "-"


def _equipment_maintenance_worksheet_xml(
    headers: list[str],
    rows: list[dict[str, Any]],
    generated_at: str,
    summary: dict[str, int | float],
) -> str:
    table_start = 10
    export_rows = rows or [{}]
    table_end = table_start + len(export_rows)
    col_count = len(headers)
    signature_start = table_end + 2
    xml_rows = [
        _xml_sparse_row(1, [(1, "OREZONE", 16), (3, "EQUIPMENT MAINTENANCE REGISTER", 1)], height=34),
        _xml_sparse_row(2, [(3, "Preventive maintenance, oil change follow-up, odometer due alerts and QHSE approval workflow.", 2)]),
        _xml_sparse_row(3, [(3, f"Generated: {generated_at} | Controlled QHSE document | Automated due-date and kilometer formulas", 3)]),
        _xml_row(
            6,
            [
                (f"Total: {summary.get('total', 0)}", 5),
                (f"Open: {summary.get('open', 0)}", 6),
                (f"Late/Due: {summary.get('late', 0)}", 8),
                (f"Km due: {summary.get('odometer_due', 0)}", 8 if summary.get("odometer_due", 0) else 5),
                (f"Critical: {summary.get('critical', 0)}", 7),
                (f"Cost: {summary.get('cost', 0)}", 6),
            ],
        ),
        _xml_sparse_row(
            8,
            [(1, "Automation: Next maintenance km = Last maintenance km + KM to add. Alert recalculates if dates or counters are edited in Excel.", 2)],
            height=26,
        ),
        _xml_row(table_start, [(header, 9) for header in headers], height=34),
    ]
    for offset, row in enumerate(export_rows, start=1):
        row_index = table_start + offset
        style = 10 if offset % 2 else 11
        xml_rows.append(_equipment_maintenance_row_xml(row_index, row, style))
    xml_rows.extend(_signature_rows(signature_start, col_count))

    last_row = signature_start + 1
    dimension = f"A1:{_column_name(col_count)}{max(last_row, table_start)}"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="{table_start}" topLeftCell="A{table_start + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols>
    <col min="1" max="1" width="14" customWidth="1"/>
    <col min="2" max="2" width="28" customWidth="1"/>
    <col min="3" max="4" width="18" customWidth="1"/>
    <col min="5" max="5" width="28" customWidth="1"/>
    <col min="6" max="8" width="15" customWidth="1"/>
    <col min="9" max="10" width="15" customWidth="1"/>
    <col min="11" max="15" width="15" customWidth="1"/>
    <col min="16" max="16" width="17" customWidth="1"/>
    <col min="17" max="17" width="13" customWidth="1"/>
    <col min="18" max="18" width="34" customWidth="1"/>
  </cols>
  <sheetData>{"".join(xml_rows)}</sheetData>
  <autoFilter ref="A{table_start}:{_column_name(col_count)}{max(table_end, table_start)}"/>
  <mergeCells count="11">
    <mergeCell ref="A1:B3"/>
    <mergeCell ref="C1:R1"/>
    <mergeCell ref="C2:R2"/>
    <mergeCell ref="C3:R3"/>
    <mergeCell ref="A8:R8"/>
    <mergeCell ref="A{signature_start}:C{signature_start}"/>
    <mergeCell ref="D{signature_start}:G{signature_start}"/>
    <mergeCell ref="H{signature_start}:K{signature_start}"/>
    <mergeCell ref="A{signature_start + 1}:C{signature_start + 1}"/>
    <mergeCell ref="D{signature_start + 1}:G{signature_start + 1}"/>
    <mergeCell ref="H{signature_start + 1}:K{signature_start + 1}"/>
  </mergeCells>
  <pageMargins left="0.25" right="0.25" top="0.45" bottom="0.45" header="0.2" footer="0.2"/>
  <pageSetup orientation="landscape" paperSize="9" fitToWidth="1" fitToHeight="0"/>
</worksheet>"""


def _equipment_maintenance_dashboard_xml(
    rows: list[dict[str, Any]],
    generated_at: str,
    summary: dict[str, int | float],
) -> str:
    completed = sum(1 for row in rows if row.get("status") == "terminee")
    completion = round(completed * 100 / max(len(rows), 1))
    types: dict[str, int] = {}
    responsible: dict[str, int] = {}
    for row in rows:
        type_name = str(row.get("maintenance_type") or "other").replace("_", " ").title()
        types[type_name] = types.get(type_name, 0) + 1
        owner = str(row.get("responsible") or "Non affecte")
        responsible[owner] = responsible.get(owner, 0) + 1
    xml_rows = [
        _xml_sparse_row(1, [(1, "OREZONE\nQHSE", 16), (4, "EQUIPMENT MAINTENANCE MANAGEMENT", 1), (13, f"Exporte le: {generated_at}", 6)], height=30),
        _xml_sparse_row(2, [(4, "TABLEAU DE BORD EXECUTIF", 17), (13, "Document controle QHSE", 12)], height=30),
        _xml_sparse_row(4, [(1, "INDICATEURS CLES (KPI)", 1)]),
        _xml_sparse_row(5, [(1, "EQUIPEMENTS SUIVIS", 12), (4, "REALISEES", 12), (7, "OUVERTES", 13), (10, "EN RETARD", 15), (13, "COUT TOTAL FCFA", 14)]),
        _xml_sparse_row(6, [(1, summary.get("total", 0), 12), (4, completed, 12), (7, summary.get("open", 0), 13), (10, summary.get("late", 0), 15), (13, f"{float(summary.get('cost', 0)):,.0f}", 14)], height=30),
        _xml_sparse_row(8, [(1, "TAUX DE REALISATION", 1), (5, "ALERTES AUTOMATIQUES", 1), (9, "COURBE DES COUTS PAR INTERVENTION", 1)]),
        _xml_sparse_row(9, [(1, f"{completion}%", 12 if completion >= 70 else 14), (5, f"Critiques: {summary.get('critical', 0)}", 15), (7, f"Compteur du: {summary.get('odometer_due', 0)}", 14)]),
        _xml_sparse_row(11, [(1, "REPARTITION PAR TYPE", 1), (5, "MAINTENANCES PAR RESPONSABLE", 1)]),
    ]
    for index in range(5):
        type_item = list(sorted(types.items(), key=lambda item: item[1], reverse=True))[index:index + 1]
        owner_item = list(sorted(responsible.items(), key=lambda item: item[1], reverse=True))[index:index + 1]
        xml_rows.append(
            _xml_sparse_row(
                13 + index,
                [
                    (1, f"{type_item[0][0]}: {type_item[0][1]}" if type_item else "-", 6),
                    (5, f"{owner_item[0][0]}: {owner_item[0][1]}" if owner_item else "-", 6),
                ],
            )
        )
    xml_rows.extend(
        [
            _xml_sparse_row(20, [(1, "ANALYSE RAPIDE", 1)]),
            _xml_sparse_row(21, [(1, f"Taux de completion: {completion}%", 12), (5, f"Maintenances en retard: {summary.get('late', 0)}", 15)]),
            _xml_sparse_row(22, [(1, f"Maintenances critiques: {summary.get('critical', 0)}", 15), (5, f"Maintenances compteur dues: {summary.get('odometer_due', 0)}", 14)]),
            _xml_sparse_row(24, [(1, "La prochaine maintenance est calculee automatiquement selon la date et le kilometrage.", 6)]),
        ]
    )
    merges = [
        "A1:C3", "D1:L1", "D2:L2", "M1:P1", "M2:P2", "A4:P4",
        *[f"{start}{row}:{end}{row}" for row in (5, 6) for start, end in (("A", "C"), ("D", "F"), ("G", "I"), ("J", "L"), ("M", "P"))],
        "A8:D8", "E8:H8", "I8:P8", "A9:D9", "E9:F9", "G9:H9",
        "A11:D11", "E11:H11", *[f"A{row}:D{row}" for row in range(13, 18)], *[f"E{row}:H{row}" for row in range(13, 18)],
        "A20:P20", "A21:D21", "E21:H21", "A22:D22", "E22:H22", "A24:P24",
    ]
    return _monthly_sheet_document(xml_rows, 16, 24, widths=[(1, 16, 13)], landscape=True, merge_refs=merges, drawing_rel_id="rId1")


def _equipment_maintenance_analysis_xml(rows: list[dict[str, Any]], summary: dict[str, int | float]) -> str:
    headers = ["#", "Equipement", "Categorie", "Site", "Responsable", "Type", "Statut", "Priorite", "Cout FCFA", "KM restant", "Date planifiee", "Prochaine date", "Alerte"]
    xml_rows = [
        _xml_sparse_row(1, [(1, "OREZONE QHSE", 16), (4, "ANALYSE DES COUTS ET ALERTES", 1)], height=34),
        _xml_sparse_row(2, [(1, f"Cout total: {float(summary.get('cost', 0)):,.0f} FCFA | Retards: {summary.get('late', 0)} | Critiques: {summary.get('critical', 0)}", 6)]),
        _xml_row(5, [(header, 1) for header in headers], height=32),
    ]
    for index, row in enumerate(sorted(rows, key=lambda item: float(item.get("cost") or 0), reverse=True), start=1):
        alert = _maintenance_alert_label(row, row.get("remaining_km"))
        values = [index, row.get("equipment_name") or "-", row.get("category") or "-", row.get("site") or "-", row.get("responsible") or "-", row.get("maintenance_type") or "-", row.get("status") or "-", row.get("priority") or "-", row.get("cost") or 0, row.get("remaining_km") if row.get("remaining_km") is not None else "", row.get("planned_date") or "-", row.get("next_due_date") or "-", alert]
        xml_rows.append(_xml_row(5 + index, [(value, _maintenance_alert_style(row) if position == 12 else 6) for position, value in enumerate(values)], height=24))
    return _monthly_sheet_document(xml_rows, len(headers), 6 + len(rows), widths=[(1, 1, 5), (2, 2, 25), (3, 8, 18), (9, 13, 16)], freeze_row=5, landscape=True, filter_ref=f"A5:{_column_name(len(headers))}{5 + len(rows)}")


def _equipment_maintenance_control_xml(
    rows: list[dict[str, Any]],
    generated_at: str,
    summary: dict[str, int | float],
) -> str:
    xml_rows = [
        _xml_sparse_row(1, [(1, "OREZONE QHSE", 16), (5, "CONTROLE & SIGNATURES", 1)], height=34),
        _xml_sparse_row(3, [(1, "INFORMATIONS DOCUMENT", 1), (7, "CONTROLES QUALITE", 1), (12, "RESUME EXECUTIF", 1)]),
        _xml_sparse_row(4, [(1, "Document: EQUIPMENT MAINTENANCE MANAGEMENT", 6), (7, f"Nombre de lignes: {len(rows)}", 6), (12, f"Total suivis: {summary.get('total', 0)}", 6)]),
        _xml_sparse_row(5, [(1, f"Date export: {generated_at}", 6), (7, f"En retard: {summary.get('late', 0)}", 15), (12, f"Cout total: {float(summary.get('cost', 0)):,.0f} FCFA", 6)]),
        _xml_sparse_row(6, [(1, "Source: OREZONE QHSE SYSTEM", 6), (7, f"Critiques: {summary.get('critical', 0)}", 15), (12, f"Ouvertes: {summary.get('open', 0)}", 6)]),
        _xml_sparse_row(8, [(1, "PREPARED BY", 9), (6, "CHECKED BY", 9), (11, "APPROVED BY", 9)]),
        _xml_sparse_row(9, [(1, "Nom / Fonction / Date / Signature", 10), (6, "Nom / Fonction / Date / Signature", 10), (11, "Nom / Fonction / Date / Signature", 10)], height=80),
        _xml_sparse_row(11, [(1, "Document genere automatiquement par le systeme OREZONE QHSE.", 1)]),
    ]
    merges = ["A1:D1", "E1:P1", "A3:F3", "G3:K3", "L3:P3", *[f"A{row}:F{row}" for row in range(4, 7)], *[f"G{row}:K{row}" for row in range(4, 7)], *[f"L{row}:P{row}" for row in range(4, 7)], "A8:E8", "F8:J8", "K8:P8", "A9:E9", "F9:J9", "K9:P9", "A11:P11"]
    return _monthly_sheet_document(xml_rows, 16, 11, widths=[(1, 16, 14)], landscape=True, merge_refs=merges)


def _equipment_maintenance_cost_chart_xml(rows: list[dict[str, Any]]) -> str:
    labels = [str(row.get("equipment_code") or row.get("equipment_name") or index + 1) for index, row in enumerate(rows[:12])]
    costs = [float(row.get("cost") or 0) for row in rows[:12]]
    due = [1 if row.get("status") == "en_retard" else 0 for row in rows[:12]]
    return (
        _monthly_line_chart_xml(labels, costs, due)
        .replace("TENDANCE JOURNALIERE", "EVOLUTION DES COUTS ET RETARDS")
        .replace("Heures travaillees", "Cout intervention")
        .replace("Employes presents", "Maintenance en retard")
    )


def _equipment_maintenance_row_xml(row_index: int, row: dict[str, Any], default_style: int) -> str:
    status_style = _maintenance_status_style(row.get("status"), row.get("priority"))
    next_km = _maintenance_next_km(row)
    remaining_km = _maintenance_remaining_km(row, next_km)
    alert = _maintenance_alert_label(row, remaining_km)
    values: list[tuple[Any, int, str | None]] = [
        (row.get("equipment_code") or "", default_style, None),
        (row.get("equipment_name") or "", default_style, None),
        (row.get("category") or "", default_style, None),
        (row.get("site") or "", default_style, None),
        (row.get("responsible") or "", default_style, None),
        (row.get("maintenance_type") or "", default_style, None),
        (row.get("priority") or "", _maintenance_priority_style(row.get("priority"), default_style), None),
        (row.get("status") or "", status_style, None),
        (row.get("planned_date") or "", default_style, None),
        (row.get("next_due_date") or "", default_style, None),
        (row.get("current_odometer") if row.get("current_odometer") is not None else "", default_style, None),
        (row.get("last_service_odometer") if row.get("last_service_odometer") is not None else "", default_style, None),
        (row.get("service_interval_km") if row.get("service_interval_km") is not None else "", default_style, None),
        (next_km if next_km is not None else "", 12, f'IF(AND(L{row_index}<>"",M{row_index}<>""),L{row_index}+M{row_index},"")'),
        (remaining_km if remaining_km is not None else "", 12, f'IF(AND(K{row_index}<>"",N{row_index}<>""),N{row_index}-K{row_index},"")'),
        (
            alert,
            _maintenance_alert_style(row),
            f'IF(H{row_index}="terminee","Closed",IF(AND(N{row_index}<>"",K{row_index}<>"",K{row_index}>=N{row_index}),"DUE KM",IF(H{row_index}="en_retard","LATE","OK")))',
        ),
        (row.get("cost") or 0, default_style, None),
        (row.get("observations") or "", default_style, None),
    ]
    return _xml_formula_row(row_index, values)


def _maintenance_next_km(row: dict[str, Any]) -> float | None:
    last_km = row.get("last_service_odometer")
    add_km = row.get("service_interval_km")
    if last_km is not None and add_km is not None:
        return float(last_km) + float(add_km)
    if row.get("next_due_odometer") is not None:
        return float(row.get("next_due_odometer") or 0)
    return None


def _maintenance_remaining_km(row: dict[str, Any], next_km: float | None) -> float | None:
    current_km = row.get("current_odometer")
    if current_km is None or next_km is None:
        return None
    return next_km - float(current_km)


def _maintenance_alert_label(row: dict[str, Any], remaining_km: float | None) -> str:
    if row.get("status") == "terminee":
        return "Closed"
    if remaining_km is not None and remaining_km <= 0:
        return "DUE KM"
    if row.get("status") == "en_retard":
        return "LATE"
    return "OK" if row else ""


def _maintenance_status_style(status: Any, priority: Any) -> int:
    text = str(status or "").lower()
    if text == "en_retard":
        return 15
    if text == "terminee":
        return 12
    if text == "annulee":
        return 19
    if str(priority or "").lower() == "critique":
        return 14
    return 13 if text == "en_cours" else 10


def _maintenance_priority_style(priority: Any, default_style: int) -> int:
    text = str(priority or "").lower()
    if text == "critique":
        return 15
    if text == "haute":
        return 14
    if text == "basse":
        return 12
    return default_style


def _maintenance_alert_style(row: dict[str, Any]) -> int:
    remaining = row.get("remaining_km")
    if row.get("status") == "en_retard" or (remaining is not None and float(remaining) <= 0):
        return 15
    if remaining is not None and float(remaining) <= 500:
        return 14
    return 12


def _toolbox_talk_worksheet_xml(
    headers: list[str],
    rows: list[dict[str, Any]],
    month_label: str,
    month_value: str,
    summary: dict[str, Any],
    generated_at: str,
) -> str:
    table_start = 7
    col_count = len(headers)
    table_end = table_start + len(rows)
    signature_start = table_end + 2
    xml_rows = [
        _xml_sparse_row(1, [(1, "OREZONE", 16), (3, "OREZONE QHSE - TOOLBOX TALK MONTHLY MEETING", 1)], height=34),
        _xml_sparse_row(2, [(3, f"Monthly meeting | Planning mensuel bilingue: {month_label} ({month_value})", 2)]),
        _xml_sparse_row(3, [(3, f"Generated: {generated_at} | Controlled QHSE document | English / French topics", 3)]),
        _xml_row(
            5,
            [
                (f"Days: {summary.get('days', 0)}", 4),
                (f"Completed: {summary.get('completed', 0)}", 5),
                (f"Missing: {summary.get('missing', 0)}", 8),
                (f"Progress: {summary.get('completion', 0)}%", 6),
            ],
        ),
        _xml_row(table_start, [(header, 9) for header in headers]),
    ]
    for offset, row in enumerate(rows, start=1):
        row_index = table_start + offset
        default_style = 10 if offset % 2 else 11
        xml_rows.append(
            _xml_row(
                row_index,
                [
                    (row.get("date_theme") or "", default_style),
                    (row.get("weekday") or "", default_style),
                    (row.get("topic_en") or "", default_style),
                    (row.get("theme_fr") or "", default_style),
                    (row.get("facilitateur") or "", default_style),
                    (row.get("site") or "", default_style),
                ],
            )
        )
    xml_rows.extend(_signature_rows(signature_start, col_count))

    last_row = signature_start + 1
    dimension = f"A1:{_column_name(col_count)}{max(last_row, table_start)}"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="{table_start}" topLeftCell="A{table_start + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols>
    <col min="1" max="1" width="14" customWidth="1"/>
    <col min="2" max="2" width="12" customWidth="1"/>
    <col min="3" max="3" width="42" customWidth="1"/>
    <col min="4" max="4" width="42" customWidth="1"/>
    <col min="5" max="5" width="22" customWidth="1"/>
    <col min="6" max="6" width="18" customWidth="1"/>
  </cols>
  <sheetData>{"".join(xml_rows)}</sheetData>
  <autoFilter ref="A{table_start}:{_column_name(col_count)}{max(table_end, table_start)}"/>
  <mergeCells count="10">
    <mergeCell ref="A1:B3"/>
    <mergeCell ref="C1:{_column_name(col_count)}1"/>
    <mergeCell ref="C2:{_column_name(col_count)}2"/>
    <mergeCell ref="C3:{_column_name(col_count)}3"/>
    <mergeCell ref="A{signature_start}:B{signature_start}"/>
    <mergeCell ref="C{signature_start}:D{signature_start}"/>
    <mergeCell ref="E{signature_start}:F{signature_start}"/>
    <mergeCell ref="A{signature_start + 1}:B{signature_start + 1}"/>
    <mergeCell ref="C{signature_start + 1}:D{signature_start + 1}"/>
    <mergeCell ref="E{signature_start + 1}:F{signature_start + 1}"/>
  </mergeCells>
  <pageMargins left="0.35" right="0.35" top="0.55" bottom="0.55" header="0.2" footer="0.2"/>
  <pageSetup orientation="landscape" paperSize="9" fitToWidth="1" fitToHeight="0"/>
</worksheet>"""


def _style_id(
    row_index: int,
    col_index: int,
    styles: list[list[str | None]] | None,
    header_row_index: int = 1,
    headers: list[str] | None = None,
    document_title: str | None = None,
) -> int:
    if row_index == 1 and header_row_index > 1:
        return 1 if col_index in (1, 3) else 11
    if row_index in (2, 3) and header_row_index > 1:
        return 11 if col_index == 1 else 6
    if row_index == header_row_index:
        if headers is not None and document_title is not None:
            day_start, day_end = _timesheet_day_bounds(headers, document_title)
            if day_start <= col_index <= day_end:
                return 12
            training_start, training_end = _training_matrix_bounds(headers, document_title)
            if training_start <= col_index <= training_end:
                return 12
        return 1
    if not styles:
        return 6
    style_row_index = row_index - header_row_index - 1
    style_key = styles[style_row_index][col_index - 1] if 0 <= style_row_index < len(styles) and col_index - 1 < len(styles[style_row_index]) else None
    return {
        "done": 2,
        "soon": 3,
        "missing": 4,
        "expired": 4,
        "danger": 4,
        "annual": 5,
        "section": 1,
        "drilling": 7,
        "standard": 8,
        "rest": 9,
        "break": 3,
        "permission": 10,
        "sick": 2,
        "holiday": 2,
        "unfilled": 11,
    }.get(str(style_key or ""), 6)


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _daily_lineup_worksheet_xml(
    headers: list[str],
    rows: list[list[Any]],
    generated_at: str,
    summary: dict[str, int],
) -> str:
    table_start = 9
    table_end = table_start + len(rows)
    col_count = len(headers)
    signature_start = table_end + 2
    xml_rows = [
        _xml_sparse_row(1, [(1, "OREZONE", 16), (3, "LIST OF OREZONE EMPLOYEE", 1)], height=34),
        _xml_sparse_row(2, [(3, "Employee master list, operational status, shift allocation and break planning.", 2)]),
        _xml_sparse_row(3, [(3, f"Generated: {generated_at} | Controlled QHSE document | Document QHSE controle", 3)]),
        _xml_row(
            6,
            [
                (f"Total: {summary.get('total', 0)}", 4),
                (f"Day: {summary.get('day', 0)}", 5),
                (f"Night: {summary.get('night', 0)}", 6),
                (f"Break/Absence: {summary.get('off', 0)}", 7),
                (f"Break due: {summary.get('due', 0)}", 8),
            ],
            start_col=1,
        ),
        _xml_row(table_start, [(header, 9) for header in headers]),
    ]
    for offset, row in enumerate(rows, start=1):
        row_index = table_start + offset
        style = 10 if offset % 2 else 11
        cells = []
        for col_index, value in enumerate(row, start=1):
            cell_style = _lineup_status_style(value, col_index, style)
            cells.append((value, cell_style))
        xml_rows.append(_xml_row(row_index, cells))
    xml_rows.extend(_signature_rows(signature_start, col_count))

    last_row = signature_start + 1
    dimension = f"A1:{_column_name(col_count)}{max(last_row, table_start)}"
    logo_ref = "A1:B3"
    title_ref = f"C1:{_column_name(col_count)}1"
    description_ref = f"C2:{_column_name(col_count)}2"
    generated_ref = f"C3:{_column_name(col_count)}3"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="{table_start}" topLeftCell="A{table_start + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols>
    <col min="1" max="1" width="6" customWidth="1"/>
    <col min="2" max="2" width="14" customWidth="1"/>
    <col min="3" max="4" width="20" customWidth="1"/>
    <col min="5" max="5" width="15" customWidth="1"/>
    <col min="6" max="6" width="26" customWidth="1"/>
    <col min="7" max="7" width="18" customWidth="1"/>
    <col min="8" max="8" width="16" customWidth="1"/>
    <col min="9" max="9" width="18" customWidth="1"/>
    <col min="10" max="10" width="26" customWidth="1"/>
    <col min="11" max="11" width="24" customWidth="1"/>
  </cols>
  <sheetData>{"".join(xml_rows)}</sheetData>
  <autoFilter ref="A{table_start}:{_column_name(col_count)}{max(table_end, table_start)}"/>
  <mergeCells count="10"><mergeCell ref="{logo_ref}"/><mergeCell ref="{title_ref}"/><mergeCell ref="{description_ref}"/><mergeCell ref="{generated_ref}"/><mergeCell ref="A{signature_start}:C{signature_start}"/><mergeCell ref="D{signature_start}:G{signature_start}"/><mergeCell ref="H{signature_start}:K{signature_start}"/><mergeCell ref="A{signature_start + 1}:C{signature_start + 1}"/><mergeCell ref="D{signature_start + 1}:G{signature_start + 1}"/><mergeCell ref="H{signature_start + 1}:K{signature_start + 1}"/></mergeCells>
  <pageMargins left="0.35" right="0.35" top="0.55" bottom="0.55" header="0.2" footer="0.2"/>
  <pageSetup orientation="landscape" paperSize="9" fitToWidth="1" fitToHeight="0"/>
</worksheet>"""


def _attendance_worksheet_xml(
    headers: list[str],
    rows: list[list[Any]],
    date_presence: str,
    generated_at: str,
    summary: dict[str, int | float],
) -> str:
    table_start = 12
    table_end = table_start + len(rows)
    col_count = len(headers)
    signature_start = table_end + 2
    full_date = _complete_date_label(date_presence)
    xml_rows = [
        _xml_sparse_row(1, [(1, "OREZONE", 16), (3, "LISTE DE PRESENCE OREZONE", 1)], height=34),
        _xml_sparse_row(2, [(3, "Daily field meeting attendance | Presence journaliere terrain | Controlled QHSE document", 2)]),
        _xml_sparse_row(3, [(3, f"Generated: {generated_at} | Orezone operational supervision and QHSE compliance", 3)]),
        _xml_sparse_row(5, [(1, "Complete date / Date complete", 4), (4, full_date, 6), (7, "Meeting facilitator / Animateur", 4), (9, "", 6)], height=24),
        _xml_sparse_row(6, [(1, "Daily meeting topic / Topic du meeting journalier", 4), (4, "", 6)], height=28),
        _xml_row(
            8,
            [
                (f"Total: {summary.get('total', 0)}", 4),
                (f"Presents: {summary.get('present', 0)}", 5),
                (f"Absents: {summary.get('absent', 0)}", 8),
                (f"Heures: {summary.get('hours', 0)}", 6),
                (f"A verifier: {summary.get('issues', 0)}", 7),
            ],
        ),
        _xml_row(table_start, [(header, 9) for header in headers]),
    ]
    for offset, row in enumerate(rows, start=1):
        row_index = table_start + offset
        if _attendance_is_section_row(row):
            xml_rows.append(_xml_sparse_row(row_index, [(1, row[0], 17)], height=24))
            continue
        default_style = 10 if offset % 2 else 11
        cells = []
        for col_index, value in enumerate(row, start=1):
            cell_style = _attendance_status_style(value, col_index, default_style)
            cells.append((value, cell_style))
        xml_rows.append(_xml_row(row_index, cells))
    xml_rows.extend(_signature_rows(signature_start, col_count))

    last_row = signature_start + 1
    dimension = f"A1:{_column_name(col_count)}{max(last_row, table_start)}"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="{table_start}" topLeftCell="A{table_start + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols>
    <col min="1" max="1" width="6" customWidth="1"/>
    <col min="2" max="3" width="20" customWidth="1"/>
    <col min="4" max="4" width="15" customWidth="1"/>
    <col min="5" max="5" width="28" customWidth="1"/>
    <col min="6" max="6" width="16" customWidth="1"/>
    <col min="7" max="7" width="16" customWidth="1"/>
    <col min="8" max="9" width="12" customWidth="1"/>
    <col min="10" max="10" width="12" customWidth="1"/>
    <col min="11" max="11" width="18" customWidth="1"/>
  </cols>
  <sheetData>{"".join(xml_rows)}</sheetData>
  <autoFilter ref="A{table_start}:{_column_name(col_count)}{max(table_end, table_start)}"/>
  {_attendance_merge_cells_xml(rows, signature_start, col_count)}
  <pageMargins left="0.35" right="0.35" top="0.55" bottom="0.55" header="0.2" footer="0.2"/>
  <pageSetup orientation="landscape" paperSize="9" fitToWidth="1" fitToHeight="0"/>
</worksheet>"""


def _attendance_grouped_rows(rows: list[dict[str, Any]]) -> list[list[Any]]:
    groups = [
        ("EXPATRIATE EMPLOYEES", [row for row in rows if str(row.get("type_employe") or "").lower() == "expatriate"]),
        ("NATIONAL EMPLOYEES", [row for row in rows if str(row.get("type_employe") or "national").lower() != "expatriate"]),
    ]
    data_rows: list[list[Any]] = []
    index = 1
    for label, group_rows in groups:
        data_rows.append([label, *["" for _ in range(10)]])
        if not group_rows:
            data_rows.append(["No employee in this section", *["" for _ in range(10)]])
            continue
        for row in group_rows:
            data_rows.append(
                [
                    index,
                    row.get("nom") or row.get("nom_complet") or "",
                    row.get("prenom") or "",
                    row.get("numero_badge") or "",
                    row.get("fonction") or "",
                    row.get("shift") or "",
                    row.get("statut") or "",
                    row.get("heure_entree") or "",
                    row.get("heure_sortie") or "",
                    row.get("heures") or 0,
                    row.get("controle") or "",
                ]
            )
            index += 1
    return data_rows


def _attendance_is_section_row(row: list[Any]) -> bool:
    first = str(row[0] if row else "").strip().upper()
    return first in {"EXPATRIATE EMPLOYEES", "NATIONAL EMPLOYEES"}


def _attendance_merge_cells_xml(rows: list[list[Any]], signature_start: int, col_count: int) -> str:
    table_start = 12
    merges = [
        "A1:B3",
        "C1:K1",
        "C2:K2",
        "C3:K3",
        "A5:C5",
        "D5:F5",
        "G5:H5",
        "I5:K5",
        "A6:C6",
        "D6:K6",
        f"A{signature_start}:C{signature_start}",
        f"D{signature_start}:G{signature_start}",
        f"H{signature_start}:K{signature_start}",
        f"A{signature_start + 1}:C{signature_start + 1}",
        f"D{signature_start + 1}:G{signature_start + 1}",
        f"H{signature_start + 1}:K{signature_start + 1}",
    ]
    for offset, row in enumerate(rows, start=1):
        if _attendance_is_section_row(row):
            row_index = table_start + offset
            merges.append(f"A{row_index}:{_column_name(col_count)}{row_index}")
    merge_xml = "".join(f'<mergeCell ref="{ref}"/>' for ref in merges)
    return f'<mergeCells count="{len(merges)}">{merge_xml}</mergeCells>'


def _complete_date_label(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value or ""))
    except ValueError:
        return str(value or "")
    return parsed.strftime("%A, %d %B %Y")


def _xml_row(
    row_index: int,
    values: list[tuple[Any, int]],
    start_col: int = 1,
    height: int | None = None,
) -> str:
    height_attr = f' ht="{height}" customHeight="1"' if height else ""
    cells = []
    for offset, item in enumerate(values):
        value, style_id = item
        col_index = start_col + offset
        ref = f"{_column_name(col_index)}{row_index}"
        style = f' s="{style_id}"' if style_id else ""
        if isinstance(value, (int, float)):
            cells.append(f'<c r="{ref}"{style}><v>{value}</v></c>')
        else:
            text = html.escape(str(value or ""))
            cells.append(f'<c r="{ref}" t="inlineStr"{style}><is><t>{text}</t></is></c>')
    return f'<row r="{row_index}"{height_attr}>{"".join(cells)}</row>'


def _xml_formula_row(
    row_index: int,
    values: list[tuple[Any, int, str | None]],
    start_col: int = 1,
    height: int | None = None,
) -> str:
    height_attr = f' ht="{height}" customHeight="1"' if height else ""
    cells = []
    for offset, item in enumerate(values):
        value, style_id, formula = item
        col_index = start_col + offset
        ref = f"{_column_name(col_index)}{row_index}"
        style = f' s="{style_id}"' if style_id else ""
        if formula:
            formula_type = ' t="str"' if value not in ("", None) and not isinstance(value, (int, float)) else ""
            cached_value = _formula_cached_value(value)
            cells.append(f'<c r="{ref}"{formula_type}{style}><f>{html.escape(formula)}</f>{cached_value}</c>')
        elif isinstance(value, (int, float)):
            cells.append(f'<c r="{ref}"{style}><v>{value}</v></c>')
        else:
            text = html.escape(str(value or ""))
            cells.append(f'<c r="{ref}" t="inlineStr"{style}><is><t>{text}</t></is></c>')
    return f'<row r="{row_index}"{height_attr}>{"".join(cells)}</row>'


def _formula_cached_value(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"<v>{value}</v>"
    text = str(value or "")
    if not text:
        return ""
    return f"<v>{html.escape(text)}</v>"


def _signature_rows(row_index: int, col_count: int) -> list[str]:
    if col_count >= 11:
        return [
            _xml_sparse_row(row_index, [(1, "Prepared by", 9), (4, "Checked by", 9), (8, "Approved by", 9)]),
            _xml_sparse_row(
                row_index + 1,
                [(1, "Name / Date / Signature", 10), (4, "Name / Date / Signature", 10), (8, "Name / Date / Signature", 10)],
                height=28,
            ),
        ]
    return [
        _xml_sparse_row(row_index, [(1, "Prepared by", 9), (3, "Checked by", 9), (5, "Approved by", 9)]),
        _xml_sparse_row(
            row_index + 1,
            [(1, "Name / Date / Signature", 10), (3, "Name / Date / Signature", 10), (5, "Name / Date / Signature", 10)],
            height=28,
        ),
    ]


def _xml_sparse_row(
    row_index: int,
    values: list[tuple[int, Any, int]],
    height: int | None = None,
) -> str:
    height_attr = f' ht="{height}" customHeight="1"' if height else ""
    cells = []
    for col_index, value, style_id in values:
        ref = f"{_column_name(col_index)}{row_index}"
        style = f' s="{style_id}"' if style_id else ""
        if isinstance(value, (int, float)):
            cells.append(f'<c r="{ref}"{style}><v>{value}</v></c>')
        else:
            text = html.escape(str(value or ""))
            cells.append(f'<c r="{ref}" t="inlineStr"{style}><is><t>{text}</t></is></c>')
    return f'<row r="{row_index}"{height_attr}>{"".join(cells)}</row>'


def _lineup_status_style(value: Any, col_index: int, default_style: int) -> int:
    text = str(value or "").lower()
    if col_index == 8 and "night" in text:
        return 13
    if col_index == 8 and "day" in text:
        return 12
    if col_index == 9 and "au travail" in text:
        return 12
    if col_index == 9 and "permission" in text:
        return 18
    if col_index == 9 and "break" in text:
        return 14
    if col_index == 9 and "malade" in text:
        return 15
    if col_index == 10 and any(item in text for item in ["retard", "aujourd"]):
        return 15
    if col_index == 11 and text:
        return 19 if "badge" in text or "planifier" in text else 14
    return default_style


def _attendance_status_style(value: Any, col_index: int, default_style: int) -> int:
    text = str(value or "").lower()
    if col_index == 6 and "night" in text:
        return 13
    if col_index == 6 and "day" in text:
        return 12
    if col_index == 7 and "present" in text:
        return 12
    if col_index == 7 and "absent" in text:
        return 15
    if col_index == 11 and text == "ok":
        return 12
    if col_index == 11 and text:
        return 19
    return default_style


def _daily_lineup_styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="9">
    <font><sz val="10"/><name val="Calibri"/><color rgb="FF172033"/></font>
    <font><b/><sz val="22"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>
    <font><sz val="10"/><name val="Calibri"/><color rgb="FF475569"/></font>
    <font><i/><sz val="10"/><name val="Calibri"/><color rgb="FF64748B"/></font>
    <font><b/><sz val="10"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>
    <font><b/><sz val="10"/><name val="Calibri"/><color rgb="FF172033"/></font>
    <font><b/><sz val="10"/><name val="Calibri"/><color rgb="FFDC2626"/></font>
    <font><b/><sz val="20"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>
    <font><b/><sz val="10"/><name val="Calibri"/><color rgb="FF1E3A8A"/></font>
  </fonts>
  <fills count="13">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1E3A8A"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFEFF6FF"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFDBEAFE"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE0F2FE"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF8FAFC"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFDCFCE7"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFEF3C7"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFEE2E2"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE0E7FF"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFFEDD5"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF00A6D6"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left style="thin"><color rgb="FFCBD5E1"/></left><right style="thin"><color rgb="FFCBD5E1"/></right><top style="thin"><color rgb="FFCBD5E1"/></top><bottom style="thin"><color rgb="FFCBD5E1"/></bottom><diagonal/></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="21">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"><alignment horizontal="center"/></xf>
    <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
    <xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <xf numFmtId="0" fontId="4" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment horizontal="center"/></xf>
    <xf numFmtId="0" fontId="5" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment horizontal="center"/></xf>
    <xf numFmtId="0" fontId="5" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment horizontal="center"/></xf>
    <xf numFmtId="0" fontId="5" fillId="8" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment horizontal="center"/></xf>
    <xf numFmtId="0" fontId="6" fillId="9" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment horizontal="center"/></xf>
    <xf numFmtId="0" fontId="4" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment horizontal="center"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
    <xf numFmtId="0" fontId="0" fillId="6" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
    <xf numFmtId="0" fontId="5" fillId="7" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
    <xf numFmtId="0" fontId="5" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
    <xf numFmtId="0" fontId="5" fillId="8" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
    <xf numFmtId="0" fontId="6" fillId="9" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
    <xf numFmtId="0" fontId="7" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="8" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="5" fillId="10" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
    <xf numFmtId="0" fontId="5" fillId="11" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
    <xf numFmtId="0" fontId="4" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" textRotation="45"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""
