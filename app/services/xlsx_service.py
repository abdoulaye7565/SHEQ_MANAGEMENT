from __future__ import annotations

import html
import zipfile
from pathlib import Path
from typing import Any

COMPANY_DESCRIPTION_EN = (
    "Orezone Gold Corporation is a mining company operating the Bombore gold mine. "
    "The QHSE management system supports field supervision, compliance, workforce control, "
    "equipment safety and operational reporting."
)
COMPANY_DESCRIPTION_FR = (
    "Orezone Gold Corporation est une societe miniere exploitant la mine d'or de Bombore. "
    "Le systeme QHSE soutient la supervision terrain, la conformite, le suivi des travailleurs, "
    "la securite des equipements et le reporting operationnel."
)


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
  <cellXfs count="12"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="2" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="1" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="1" fillId="6" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/><xf numFmtId="0" fontId="2" fillId="7" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="2" fillId="8" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="1" fillId="9" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="1" fillId="10" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="2" fillId="11" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/></cellXfs>
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
    data_rows = [
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
        for index, row in enumerate(rows, start=1)
    ]
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


def _worksheet_xml(
    headers: list[str],
    rows: list[list[Any]],
    styles: list[list[str | None]] | None = None,
    include_company_description: bool = False,
    document_title: str | None = None,
) -> str:
    header_row_index = 5 if include_company_description else 1
    all_rows = []
    if include_company_description:
        all_rows.extend(
            [
                ["OREZONE", document_title or "OREZONE QHSE EXPORT"],
                ["OREZONE DESCRIPTION", COMPANY_DESCRIPTION_EN],
                ["Description OREZONE", COMPANY_DESCRIPTION_FR],
                [],
            ]
        )
    all_rows.extend([headers, *rows])
    xml_rows = []
    for row_index, row in enumerate(all_rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{_column_name(col_index)}{row_index}"
            style_id = _style_id(row_index, col_index, styles, header_row_index)
            style = f' s="{style_id}"' if style_id else ""
            if isinstance(value, (int, float)):
                cells.append(f'<c r="{ref}"{style}><v>{value}</v></c>')
            else:
                text = html.escape(str(value or ""))
                cells.append(f'<c r="{ref}" t="inlineStr"{style}><is><t>{text}</t></is></c>')
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    col_count = max(len(headers), 2)
    last_row = max(len(all_rows), 1)
    dimension = f"A1:{_column_name(col_count)}{last_row}"
    header_filter_ref = f"A{header_row_index}:{_column_name(len(headers))}{last_row}"
    merge_xml = ""
    if include_company_description:
        title_ref = f"B1:{_column_name(col_count)}1"
        desc_en_ref = f"B2:{_column_name(col_count)}2"
        desc_fr_ref = f"B3:{_column_name(col_count)}3"
        merge_xml = (
            '<mergeCells count="3">'
            f'<mergeCell ref="{title_ref}"/>'
            f'<mergeCell ref="{desc_en_ref}"/>'
            f'<mergeCell ref="{desc_fr_ref}"/>'
            "</mergeCells>"
        )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="{header_row_index}" topLeftCell="A{header_row_index + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols><col min="1" max="{col_count}" width="18" customWidth="1"/></cols>
  <sheetData>{"".join(xml_rows)}</sheetData>
  <autoFilter ref="{header_filter_ref}"/>
  {merge_xml}
</worksheet>"""


def _toolbox_talk_worksheet_xml(
    headers: list[str],
    rows: list[dict[str, Any]],
    month_label: str,
    month_value: str,
    summary: dict[str, Any],
    generated_at: str,
) -> str:
    table_start = 11
    col_count = len(headers)
    table_end = table_start + len(rows)
    xml_rows = [
        _xml_sparse_row(1, [(1, "OREZONE", 16), (3, "OREZONE QHSE - TOOLBOX TALK MONTHLY MEETING", 1)], height=34),
        _xml_sparse_row(2, [(3, f"Monthly meeting | Planning mensuel bilingue: {month_label} ({month_value})", 2)]),
        _xml_sparse_row(3, [(3, f"Generated: {generated_at} | Controlled QHSE document | English / French topics", 3)]),
        _xml_sparse_row(5, [(1, "OREZONE DESCRIPTION", 4), (3, COMPANY_DESCRIPTION_EN, 2)]),
        _xml_sparse_row(6, [(1, "Description OREZONE", 4), (3, COMPANY_DESCRIPTION_FR, 2)]),
        _xml_sparse_row(7, [(1, "OBJECTIVE", 5), (3, "Confirm the daily topic, collect signatures and track missing Toolbox Talk days.", 2)]),
        _xml_row(
            9,
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

    dimension = f"A1:{_column_name(col_count)}{max(table_end, table_start)}"
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
    <mergeCell ref="A5:B5"/>
    <mergeCell ref="C5:{_column_name(col_count)}5"/>
    <mergeCell ref="A6:B6"/>
    <mergeCell ref="C6:{_column_name(col_count)}6"/>
    <mergeCell ref="A7:B7"/>
    <mergeCell ref="C7:{_column_name(col_count)}7"/>
  </mergeCells>
  <pageMargins left="0.35" right="0.35" top="0.55" bottom="0.55" header="0.2" footer="0.2"/>
  <pageSetup orientation="landscape" paperSize="9" fitToWidth="1" fitToHeight="0"/>
</worksheet>"""


def _style_id(
    row_index: int,
    col_index: int,
    styles: list[list[str | None]] | None,
    header_row_index: int = 1,
) -> int:
    if row_index == 1 and header_row_index > 1:
        return 1 if col_index == 1 else 11
    if row_index in (2, 3) and header_row_index > 1:
        return 11 if col_index == 1 else 6
    if row_index == header_row_index:
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
    table_start = 11
    table_end = table_start + len(rows)
    col_count = len(headers)
    xml_rows = [
        _xml_sparse_row(1, [(1, "OREZONE", 16), (3, "LIST OF OREZONE EMPLOYEE", 1)], height=34),
        _xml_sparse_row(2, [(3, "Employee master list, operational status, shift allocation and break planning.", 2)]),
        _xml_sparse_row(3, [(3, f"Generated: {generated_at}", 3)]),
        _xml_sparse_row(4, [(1, "OREZONE DESCRIPTION", 4), (3, COMPANY_DESCRIPTION_EN, 2)]),
        _xml_sparse_row(5, [(1, "Description OREZONE", 4), (3, COMPANY_DESCRIPTION_FR, 2)]),
        _xml_row(
            8,
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

    dimension = f"A1:{_column_name(col_count)}{max(table_end, table_start)}"
    logo_ref = "A1:B3"
    title_ref = f"C1:{_column_name(col_count)}1"
    description_ref = f"C2:{_column_name(col_count)}2"
    generated_ref = f"C3:{_column_name(col_count)}3"
    company_en_ref = f"C4:{_column_name(col_count)}4"
    company_fr_ref = f"C5:{_column_name(col_count)}5"
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
  <mergeCells count="8"><mergeCell ref="{logo_ref}"/><mergeCell ref="{title_ref}"/><mergeCell ref="{description_ref}"/><mergeCell ref="{generated_ref}"/><mergeCell ref="A4:B4"/><mergeCell ref="{company_en_ref}"/><mergeCell ref="A5:B5"/><mergeCell ref="{company_fr_ref}"/></mergeCells>
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
    table_start = 11
    table_end = table_start + len(rows)
    col_count = len(headers)
    xml_rows = [
        _xml_sparse_row(1, [(1, "OREZONE", 16), (3, "LISTE DE PRESENCE OREZONE", 1)], height=34),
        _xml_sparse_row(2, [(3, f"Date de presence: {date_presence}", 2)]),
        _xml_sparse_row(3, [(3, f"Generated: {generated_at}", 3)]),
        _xml_sparse_row(4, [(1, "OREZONE DESCRIPTION", 4), (3, COMPANY_DESCRIPTION_EN, 2)]),
        _xml_sparse_row(5, [(1, "Description OREZONE", 4), (3, COMPANY_DESCRIPTION_FR, 2)]),
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
        default_style = 10 if offset % 2 else 11
        cells = []
        for col_index, value in enumerate(row, start=1):
            cell_style = _attendance_status_style(value, col_index, default_style)
            cells.append((value, cell_style))
        xml_rows.append(_xml_row(row_index, cells))

    dimension = f"A1:{_column_name(col_count)}{max(table_end, table_start)}"
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
  <mergeCells count="8"><mergeCell ref="A1:B3"/><mergeCell ref="C1:K1"/><mergeCell ref="C2:K2"/><mergeCell ref="C3:K3"/><mergeCell ref="A4:B4"/><mergeCell ref="C4:K4"/><mergeCell ref="A5:B5"/><mergeCell ref="C5:K5"/></mergeCells>
  <pageMargins left="0.35" right="0.35" top="0.55" bottom="0.55" header="0.2" footer="0.2"/>
  <pageSetup orientation="landscape" paperSize="9" fitToWidth="1" fitToHeight="0"/>
</worksheet>"""


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
