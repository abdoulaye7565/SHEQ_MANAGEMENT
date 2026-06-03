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
        "Current km",
        "Last service km",
        "Interval km",
        "Next maintenance km",
        "Km remaining",
        "Alert",
        "Cost",
        "Observations",
    ]
    sheet_xml = _equipment_maintenance_worksheet_xml(headers, rows, generated_at, summary)
    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Equipment Maintenance" sheetId="1" r:id="rId1"/></sheets>
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
    all_rows = [
        ["OREZONE", "", title],
        ["", "", "Controlled QHSE document | Document QHSE controle"],
        ["", "", OREZONE_HEADER_NOTE],
        [],
        ["Summary", f"Rows: {len(rows)}"],
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
            [(1, "Automation: Next maintenance km = Last service km + Interval km. Alert recalculates if dates or counters are edited in Excel.", 2)],
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


def _equipment_maintenance_row_xml(row_index: int, row: dict[str, Any], default_style: int) -> str:
    status_style = _maintenance_status_style(row.get("status"), row.get("priority"))
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
        ("", 12, f'IF(AND(L{row_index}<>"",M{row_index}<>""),L{row_index}+M{row_index},"")'),
        ("", 12, f'IF(AND(K{row_index}<>"",N{row_index}<>""),N{row_index}-K{row_index},"")'),
        (
            "",
            _maintenance_alert_style(row),
            f'IF(H{row_index}="terminee","Closed",IF(AND(N{row_index}<>"",K{row_index}>=N{row_index}),"DUE KM",IF(AND(J{row_index}<>"",DATEVALUE(J{row_index})<=TODAY()),"DUE DATE",IF(AND(I{row_index}<>"",DATEVALUE(I{row_index})<TODAY()),"LATE","OK"))))',
        ),
        (row.get("cost") or 0, default_style, None),
        (row.get("observations") or "", default_style, None),
    ]
    return _xml_formula_row(row_index, values)


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
            cells.append(f'<c r="{ref}"{style}><f>{html.escape(formula)}</f></c>')
        elif isinstance(value, (int, float)):
            cells.append(f'<c r="{ref}"{style}><v>{value}</v></c>')
        else:
            text = html.escape(str(value or ""))
            cells.append(f'<c r="{ref}" t="inlineStr"{style}><is><t>{text}</t></is></c>')
    return f'<row r="{row_index}"{height_attr}>{"".join(cells)}</row>'


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
  <fills count="12">
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
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left style="thin"><color rgb="FFCBD5E1"/></left><right style="thin"><color rgb="FFCBD5E1"/></right><top style="thin"><color rgb="FFCBD5E1"/></top><bottom style="thin"><color rgb="FFCBD5E1"/></bottom><diagonal/></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="20">
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
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""
