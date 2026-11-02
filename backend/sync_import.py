"""Import employees/tasks/attendance from encrypted customer cloud snapshots."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from . import db as database
from .auth import require_user

router = APIRouter()


class SyncImportIn(BaseModel):
    employees: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    attendance: list[dict[str, Any]] = []
    clear_existing: bool = False


@router.post("/api/sync/import")
def sync_import(body: SyncImportIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    counts = {"employees": 0, "tasks": 0, "attendance": 0}
    with database.db() as conn:
        if body.clear_existing:
            conn.execute("DELETE FROM attendance")
            conn.execute("DELETE FROM tasks")
            conn.execute("DELETE FROM employees")
        for e in body.employees:
            name = (e.get("name") or e.get("employee_name") or "").strip()
            if not name:
                continue
            role = e.get("role") or e.get("job_title") or e.get("department") or ""
            phone = e.get("phone") or ""
            email = e.get("email") or ""
            status = e.get("status") or "Active"
            existing = conn.execute(
                "SELECT id FROM employees WHERE name = ? COLLATE NOCASE", (name,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE employees SET role=?, phone=?, email=?, status=?, updated_at=? WHERE id=?",
                    (role, phone, email, status, now, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO employees (name, role, phone, email, status, notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                    (name, role, phone, email, status, "", now, now),
                )
            counts["employees"] += 1
        for t in body.tasks:
            title = (t.get("title") or "").strip()
            if not title:
                continue
            assignee = t.get("assignee") or t.get("employee_name") or ""
            if not assignee and t.get("employee_id"):
                row = conn.execute(
                    "SELECT name FROM employees WHERE id = ?", (t.get("employee_id"),)
                ).fetchone()
                if row:
                    assignee = row["name"]
            status = t.get("status") or "Open"
            priority = t.get("priority") or "Normal"
            due = t.get("due_date") or t.get("task_date") or ""
            existing = conn.execute(
                "SELECT id FROM tasks WHERE title = ? AND COALESCE(assignee,'') = ? AND COALESCE(due_date,'') = ?",
                (title, assignee, due),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE tasks SET status=?, priority=?, updated_at=? WHERE id=?",
                    (status, priority, now, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO tasks (title, description, assignee, status, priority, due_date, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                    (title, t.get("details") or t.get("description") or "", assignee, status, priority, due, now, now),
                )
            counts["tasks"] += 1
        for a in body.attendance:
            emp = (a.get("employee_name") or a.get("name") or "").strip()
            work_date = a.get("work_date") or a.get("date") or ""
            if not emp or not work_date:
                continue
            status = a.get("status") or a.get("attendance_status") or "Present"
            if status == "Unmarked":
                continue
            check_in = a.get("check_in") or ""
            check_out = a.get("check_out") or ""
            existing = conn.execute(
                "SELECT id FROM attendance WHERE employee_name = ? AND work_date = ?",
                (emp, work_date),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE attendance SET status=?, check_in=?, check_out=? WHERE id=?",
                    (status, check_in, check_out, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO attendance (employee_id, employee_name, work_date, status, check_in, check_out, notes, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (None, emp, work_date, status, check_in, check_out, a.get("note") or a.get("attendance_note") or "", now),
                )
            counts["attendance"] += 1
    return {"ok": True, "imported": counts}


@router.get("/api/sync/status")
def sync_status(user=Depends(require_user)):
    with database.db() as conn:
        return {
            "employees": conn.execute("SELECT COUNT(*) c FROM employees").fetchone()["c"],
            "tasks": conn.execute("SELECT COUNT(*) c FROM tasks").fetchone()["c"],
            "attendance": conn.execute("SELECT COUNT(*) c FROM attendance").fetchone()["c"],
        }
