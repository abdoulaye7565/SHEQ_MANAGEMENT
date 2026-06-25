from __future__ import annotations

import json
import uuid
from datetime import date
from typing import Any

from app.db.connection import db_session


# ── Equipment ────────────────────────────────────────────────────────────────

def list_equipment(active_only: bool = True) -> list[dict[str, Any]]:
    q = "SELECT * FROM drilling_equipment"
    if active_only:
        q += " WHERE active=1"
    q += " ORDER BY sort_order, id"
    with db_session() as conn:
        return [dict(r) for r in conn.execute(q).fetchall()]


def add_equipment(name: str, code: str, unit: str = "Litre") -> int:
    with db_session() as conn:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order),0) FROM drilling_equipment"
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO drilling_equipment(name, code, unit, sort_order) VALUES (?,?,?,?)",
            (name.strip(), code.strip().upper(), unit, int(max_order) + 1),
        )
        return int(cur.lastrowid)


def update_equipment(eq_id: int, name: str, code: str, unit: str, active: bool) -> None:
    with db_session() as conn:
        conn.execute(
            "UPDATE drilling_equipment SET name=?, code=?, unit=?, active=? WHERE id=?",
            (name.strip(), code.strip().upper(), unit, 1 if active else 0, eq_id),
        )


def delete_equipment(eq_id: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM drilling_equipment WHERE id=?", (eq_id,))


# ── Internal helpers ─────────────────────────────────────────────────────────

def _insert_log_entry(conn, report_id: int, order: int, entry: dict[str, Any]) -> None:
    df = entry.get("depth_from")
    dt = entry.get("depth_to")
    run = entry.get("run")
    if df is not None and dt is not None:
        try:
            run = float(dt) - float(df)
        except (TypeError, ValueError):
            pass
    conn.execute(
        """INSERT INTO drilling_log_entries
           (report_id, row_order, bh_number, depth_from, depth_to, run,
            advance, time_hours, comments)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            report_id,
            order,
            str(entry.get("bh_number") or "") or None,
            float(df) if df is not None else None,
            float(dt) if dt is not None else None,
            float(run) if run is not None else None,
            float(entry["advance"]) if entry.get("advance") is not None else None,
            float(entry["time_hours"]) if entry.get("time_hours") is not None else None,
            str(entry.get("comments") or "") or None,
        ),
    )


def _report_params(data: dict[str, Any]) -> tuple:
    return (
        str(data.get("shift") or "DAY"),
        str(data.get("report_date") or date.today().isoformat()),
        str(data.get("rig_type") or "") or None,
        str(data.get("rig_number") or "") or None,
        str(data.get("contract_location") or "") or None,
        str(data.get("hole_number") or "") or None,
        float(data["angle"]) if data.get("angle") is not None else None,
        str(data.get("client") or "") or None,
        float(data.get("total_advance") or 0),
        json.dumps(data.get("diesel") or {}),
        str(data.get("refueler_name") or "") or None,
        str(data.get("operator_name") or "") or None,
        str(data.get("supervisor_name") or "") or None,
        str(data.get("status") or "draft"),
        int(data["site_id"]) if data.get("site_id") else None,
        str(data.get("created_by") or "") or None,
    )


# ── Reports CRUD ─────────────────────────────────────────────────────────────

def create_drilling_report(data: dict[str, Any]) -> int:
    report_uuid = data.get("uuid") or str(uuid.uuid4())
    params = _report_params(data)
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO drilling_reports
               (uuid, shift, report_date, rig_type, rig_number, contract_location,
                hole_number, angle, client, total_advance, diesel_json, refueler_name,
                operator_name, supervisor_name, status, site_id, created_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (report_uuid, *params),
        )
        report_id = int(cur.lastrowid)
        for i, entry in enumerate(data.get("entries") or []):
            _insert_log_entry(conn, report_id, i, entry)
        return report_id


def update_drilling_report(report_id: int, data: dict[str, Any]) -> None:
    params = _report_params(data)
    with db_session() as conn:
        conn.execute(
            """UPDATE drilling_reports SET
               shift=?, report_date=?, rig_type=?, rig_number=?, contract_location=?,
               hole_number=?, angle=?, client=?, total_advance=?, diesel_json=?,
               refueler_name=?, operator_name=?, supervisor_name=?, status=?,
               site_id=?, created_by=?
               WHERE id=?""",
            (*params, report_id),
        )
        if "entries" in data:
            conn.execute(
                "DELETE FROM drilling_log_entries WHERE report_id=?", (report_id,)
            )
            for i, entry in enumerate(data["entries"]):
                _insert_log_entry(conn, report_id, i, entry)


def validate_drilling_report(report_id: int, supervisor_name: str) -> None:
    with db_session() as conn:
        conn.execute(
            """UPDATE drilling_reports
               SET status='validated', supervisor_name=?, validated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (supervisor_name, report_id),
        )


def reject_drilling_report(report_id: int) -> None:
    with db_session() as conn:
        conn.execute(
            "UPDATE drilling_reports SET status='submitted' WHERE id=? AND status='validated'",
            (report_id,),
        )


def delete_drilling_report(report_id: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM drilling_reports WHERE id=?", (report_id,))


# ── Queries ──────────────────────────────────────────────────────────────────

def get_drilling_report(report_id: int) -> dict[str, Any] | None:
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM drilling_reports WHERE id=?", (report_id,)
        ).fetchone()
        if not row:
            return None
        report = dict(row)
        report["diesel"] = json.loads(report.get("diesel_json") or "{}")
        entries = conn.execute(
            "SELECT * FROM drilling_log_entries WHERE report_id=? ORDER BY row_order",
            (report_id,),
        ).fetchall()
        report["entries"] = [dict(e) for e in entries]
        return report


def get_drilling_report_by_uuid(report_uuid: str) -> dict[str, Any] | None:
    with db_session() as conn:
        row = conn.execute(
            "SELECT id FROM drilling_reports WHERE uuid=?", (report_uuid,)
        ).fetchone()
    if not row:
        return None
    return get_drilling_report(int(row["id"]))


def list_drilling_reports(
    status: str | None = None,
    location: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if status and status != "all":
        conditions.append("status=?")
        params.append(status)
    if location:
        conditions.append("contract_location LIKE ?")
        params.append(f"%{location}%")
    if date_from:
        conditions.append("report_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("report_date <= ?")
        params.append(date_to)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params += [limit, offset]
    with db_session() as conn:
        rows = conn.execute(
            f"SELECT * FROM drilling_reports {where} ORDER BY report_date DESC, id DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def count_drilling_reports(
    status: str | None = None,
    location: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> int:
    conditions: list[str] = []
    params: list[Any] = []
    if status and status != "all":
        conditions.append("status=?")
        params.append(status)
    if location:
        conditions.append("contract_location LIKE ?")
        params.append(f"%{location}%")
    if date_from:
        conditions.append("report_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("report_date <= ?")
        params.append(date_to)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    with db_session() as conn:
        return int(
            conn.execute(
                f"SELECT COUNT(*) FROM drilling_reports {where}", params
            ).fetchone()[0]
        )


def get_drilling_kpis() -> dict[str, Any]:
    today_str = date.today().isoformat()
    with db_session() as conn:
        total     = conn.execute("SELECT COUNT(*) FROM drilling_reports").fetchone()[0]
        validated = conn.execute("SELECT COUNT(*) FROM drilling_reports WHERE status='validated'").fetchone()[0]
        pending   = conn.execute("SELECT COUNT(*) FROM drilling_reports WHERE status='submitted'").fetchone()[0]
        draft     = conn.execute("SELECT COUNT(*) FROM drilling_reports WHERE status='draft'").fetchone()[0]
        adv       = conn.execute(
            "SELECT COALESCE(SUM(total_advance),0) FROM drilling_reports WHERE status='validated'"
        ).fetchone()[0]
        today_c   = conn.execute(
            "SELECT COUNT(*) FROM drilling_reports WHERE report_date=?", (today_str,)
        ).fetchone()[0]
    return {
        "total": int(total),
        "validated": int(validated),
        "pending": int(pending),
        "draft": int(draft),
        "total_advance_m": float(adv),
        "today": int(today_c),
    }


# ── Sync helpers (used by mobile_sync_service) ───────────────────────────────

def upsert_from_mobile(payload: dict[str, Any]) -> int:
    """Insert or update a drilling report received from mobile sync."""
    existing = get_drilling_report_by_uuid(payload["uuid"])
    if existing:
        update_drilling_report(existing["id"], payload)
        return existing["id"]
    return create_drilling_report(payload)


def list_validated_since(since_iso: str | None = None) -> list[dict[str, Any]]:
    """Return validated reports (with entries) for desktop sync display."""
    cond = "WHERE status='validated'"
    params: list[Any] = []
    if since_iso:
        cond += " AND (synced_at IS NULL OR synced_at < ?)"
        params.append(since_iso)
    with db_session() as conn:
        rows = conn.execute(
            f"SELECT * FROM drilling_reports {cond} ORDER BY validated_at DESC",
            params,
        ).fetchall()
    result = []
    for row in rows:
        r = dict(row)
        r["diesel"] = json.loads(r.get("diesel_json") or "{}")
        with db_session() as conn:
            entries = conn.execute(
                "SELECT * FROM drilling_log_entries WHERE report_id=? ORDER BY row_order",
                (r["id"],),
            ).fetchall()
        r["entries"] = [dict(e) for e in entries]
        result.append(r)
    return result
