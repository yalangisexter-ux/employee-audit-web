"""Independent Employee Audit Manager web API + SPA."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db as database
from .auth import authenticate, create_session, is_customer_admin, is_developer, require_user
from .sync_import import router as sync_router

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

app = FastAPI(title="Employee Audit Manager Web", version="2.2.0")
app.include_router(sync_router)


@app.on_event("startup")
def _startup() -> None:
    database.init_db()


class LoginIn(BaseModel):
    username: str
    password: str


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=12, max_length=256)


class EmployeeIn(BaseModel):
    name: str
    role: str = ""
    phone: str = ""
    email: str = ""
    status: str = "Active"
    notes: str = ""


class TaskIn(BaseModel):
    title: str
    description: str = ""
    assignee: str = ""
    status: str = "Open"
    priority: str = "Normal"
    due_date: str = ""


class AttendanceIn(BaseModel):
    employee_id: Optional[int] = None
    employee_name: str
    work_date: str
    status: str = "Present"
    check_in: str = ""
    check_out: str = ""
    notes: str = ""


class ProductIn(BaseModel):
    name: str
    sku: str = ""
    category: str = ""
    stock: int = 0
    price: float = 0
    notes: str = ""


class ServiceIn(BaseModel):
    name: str
    category: str = ""
    price: float = 0
    duration_min: int = 0
    notes: str = ""


class OrderIn(BaseModel):
    customer_name: str
    item: str
    quantity: int = 1
    amount: float = 0
    status: str = "Pending"
    order_date: str = Field(default_factory=lambda: date.today().isoformat())
    notes: str = ""


class MemberIn(BaseModel):
    name: str
    phone: str = ""
    plan: str = ""
    status: str = "Active"
    start_date: str = ""
    notes: str = ""


class CustomerIn(BaseModel):
    business_name: str
    contact_name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    kind: str = "Prospect"
    status: str = "New"
    notes: str = ""


class ActivityIn(BaseModel):
    title: str
    category: str = ""
    employee_name: str = ""
    activity_date: str = ""
    notes: str = ""


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "app": "employee-audit-web", "version": app.version}


@app.get("/api/auth/status")
def auth_status() -> dict[str, Any]:
    with database.db() as conn:
        users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    return {"setup_required": users == 0, "user_count": users}


@app.post("/api/auth/login")
def login(body: LoginIn) -> dict[str, Any]:
    user = authenticate(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session(int(user["id"]))
    return {"token": token, "user": {"id": user["id"], "username": user["username"], "display_name": user["display_name"], "role": user["role"], "is_customer": is_customer_admin(user), "is_developer": is_developer(user)}}


@app.post("/api/auth/change-password")
def change_password(body: PasswordChangeIn, user=Depends(require_user)) -> dict[str, Any]:
    if not database.verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if database.verify_password(body.new_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="New password must be different from the current password")
    with database.db() as conn:
        conn.execute(
            "UPDATE users SET password_hash=?, password_hash_alt=NULL WHERE id=?",
            (database.hash_password(body.new_password), user["id"]),
        )
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
    token = create_session(int(user["id"]))
    return {"ok": True, "message": "Password updated successfully", "token": token}


@app.get("/api/auth/me")
def me(user=Depends(require_user)) -> dict[str, Any]:
    return {"id": user["id"], "username": user["username"], "display_name": user["display_name"], "role": user["role"], "is_customer": is_customer_admin(user), "is_developer": is_developer(user)}


@app.get("/api/dashboard")
def dashboard(user=Depends(require_user)) -> dict[str, Any]:
    with database.db() as conn:
        return {
            "employees": conn.execute("SELECT COUNT(*) c FROM employees").fetchone()["c"],
            "tasks_open": conn.execute("SELECT COUNT(*) c FROM tasks WHERE status NOT IN ('Done','Closed','Completed')").fetchone()["c"],
            "tasks_total": conn.execute("SELECT COUNT(*) c FROM tasks").fetchone()["c"],
            "attendance_today": conn.execute("SELECT COUNT(*) c FROM attendance WHERE work_date = ?", (date.today().isoformat(),)).fetchone()["c"],
            "orders_open": conn.execute("SELECT COUNT(*) c FROM orders WHERE status != 'Completed'").fetchone()["c"],
            "members": conn.execute("SELECT COUNT(*) c FROM members").fetchone()["c"],
            "customers": conn.execute("SELECT COUNT(*) c FROM customers").fetchone()["c"],
            "products": conn.execute("SELECT COUNT(*) c FROM products").fetchone()["c"],
            "services": conn.execute("SELECT COUNT(*) c FROM services").fetchone()["c"],
            "user": user["display_name"],
            "username": user["username"],
        }


def _list(table: str, order: str = "id DESC") -> list[dict[str, Any]]:
    with database.db() as conn:
        return database.rows_to_list(conn.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall())


def _get(table: str, item_id: int) -> dict[str, Any]:
    with database.db() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        return database.row_to_dict(row)  # type: ignore


def _delete(table: str, item_id: int) -> dict[str, str]:
    with database.db() as conn:
        cur = conn.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Not found")
    return {"ok": "deleted"}


@app.get("/api/employees")
def employees_list(user=Depends(require_user)):
    return _list("employees")


@app.post("/api/employees")
def employees_create(body: EmployeeIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("INSERT INTO employees (name, role, phone, email, status, notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)", (body.name, body.role, body.phone, body.email, body.status, body.notes, now, now))
        eid = cur.lastrowid
    return _get("employees", int(eid))


@app.put("/api/employees/{item_id}")
def employees_update(item_id: int, body: EmployeeIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("UPDATE employees SET name=?, role=?, phone=?, email=?, status=?, notes=?, updated_at=? WHERE id=?", (body.name, body.role, body.phone, body.email, body.status, body.notes, now, item_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Not found")
    return _get("employees", item_id)


@app.delete("/api/employees/{item_id}")
def employees_delete(item_id: int, user=Depends(require_user)):
    return _delete("employees", item_id)


@app.get("/api/tasks")
def tasks_list(user=Depends(require_user)):
    return _list("tasks")


@app.post("/api/tasks")
def tasks_create(body: TaskIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("INSERT INTO tasks (title, description, assignee, status, priority, due_date, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)", (body.title, body.description, body.assignee, body.status, body.priority, body.due_date, now, now))
        tid = cur.lastrowid
    return _get("tasks", int(tid))


@app.put("/api/tasks/{item_id}")
def tasks_update(item_id: int, body: TaskIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("UPDATE tasks SET title=?, description=?, assignee=?, status=?, priority=?, due_date=?, updated_at=? WHERE id=?", (body.title, body.description, body.assignee, body.status, body.priority, body.due_date, now, item_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Not found")
    return _get("tasks", item_id)


@app.delete("/api/tasks/{item_id}")
def tasks_delete(item_id: int, user=Depends(require_user)):
    return _delete("tasks", item_id)


@app.get("/api/attendance")
def attendance_list(work_date: Optional[str] = None, user=Depends(require_user)):
    with database.db() as conn:
        if work_date:
            rows = conn.execute("SELECT * FROM attendance WHERE work_date = ? ORDER BY employee_name", (work_date,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM attendance ORDER BY work_date DESC, id DESC LIMIT 500").fetchall()
        return database.rows_to_list(rows)


@app.post("/api/attendance")
def attendance_create(body: AttendanceIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("INSERT INTO attendance (employee_id, employee_name, work_date, status, check_in, check_out, notes, created_at) VALUES (?,?,?,?,?,?,?,?)", (body.employee_id, body.employee_name, body.work_date, body.status, body.check_in, body.check_out, body.notes, now))
        aid = cur.lastrowid
    return _get("attendance", int(aid))


@app.put("/api/attendance/{item_id}")
def attendance_update(item_id: int, body: AttendanceIn, user=Depends(require_user)):
    with database.db() as conn:
        try:
            cur = conn.execute(
                "UPDATE attendance SET employee_id=?, employee_name=?, work_date=?, status=?, check_in=?, check_out=?, notes=? WHERE id=?",
                (body.employee_id, body.employee_name, body.work_date, body.status, body.check_in, body.check_out, body.notes, item_id),
            )
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                raise HTTPException(409, "Attendance already exists for this employee and date") from exc
            raise
        if cur.rowcount == 0:
            raise HTTPException(404, "Not found")
    return _get("attendance", item_id)


@app.delete("/api/attendance/{item_id}")
def attendance_delete(item_id: int, user=Depends(require_user)):
    return _delete("attendance", item_id)


@app.get("/api/business/products")
def products_list(user=Depends(require_user)):
    return _list("products")


@app.post("/api/business/products")
def products_create(body: ProductIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("INSERT INTO products (name, sku, category, stock, price, notes, updated_at) VALUES (?,?,?,?,?,?,?)", (body.name, body.sku, body.category, body.stock, body.price, body.notes, now))
        return _get("products", int(cur.lastrowid))


@app.put("/api/business/products/{item_id}")
def products_update(item_id: int, body: ProductIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("UPDATE products SET name=?, sku=?, category=?, stock=?, price=?, notes=?, updated_at=? WHERE id=?", (body.name, body.sku, body.category, body.stock, body.price, body.notes, now, item_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Not found")
    return _get("products", item_id)


@app.delete("/api/business/products/{item_id}")
def products_delete(item_id: int, user=Depends(require_user)):
    return _delete("products", item_id)


@app.get("/api/business/services")
def services_list(user=Depends(require_user)):
    return _list("services")


@app.post("/api/business/services")
def services_create(body: ServiceIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("INSERT INTO services (name, category, price, duration_min, notes, updated_at) VALUES (?,?,?,?,?,?)", (body.name, body.category, body.price, body.duration_min, body.notes, now))
        return _get("services", int(cur.lastrowid))


@app.put("/api/business/services/{item_id}")
def services_update(item_id: int, body: ServiceIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("UPDATE services SET name=?, category=?, price=?, duration_min=?, notes=?, updated_at=? WHERE id=?", (body.name, body.category, body.price, body.duration_min, body.notes, now, item_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Not found")
    return _get("services", item_id)


@app.delete("/api/business/services/{item_id}")
def services_delete(item_id: int, user=Depends(require_user)):
    return _delete("services", item_id)


@app.get("/api/business/orders")
def orders_list(user=Depends(require_user)):
    return _list("orders")


@app.post("/api/business/orders")
def orders_create(body: OrderIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("INSERT INTO orders (customer_name, item, quantity, amount, status, order_date, notes, created_at) VALUES (?,?,?,?,?,?,?,?)", (body.customer_name, body.item, body.quantity, body.amount, body.status, body.order_date, body.notes, now))
        return _get("orders", int(cur.lastrowid))


@app.put("/api/business/orders/{item_id}")
def orders_update(item_id: int, body: OrderIn, user=Depends(require_user)):
    with database.db() as conn:
        cur = conn.execute("UPDATE orders SET customer_name=?, item=?, quantity=?, amount=?, status=?, order_date=?, notes=? WHERE id=?", (body.customer_name, body.item, body.quantity, body.amount, body.status, body.order_date, body.notes, item_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Not found")
    return _get("orders", item_id)


@app.delete("/api/business/orders/{item_id}")
def orders_delete(item_id: int, user=Depends(require_user)):
    return _delete("orders", item_id)


@app.get("/api/business/members")
def members_list(user=Depends(require_user)):
    return _list("members")


@app.post("/api/business/members")
def members_create(body: MemberIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("INSERT INTO members (name, phone, plan, status, start_date, notes, created_at) VALUES (?,?,?,?,?,?,?)", (body.name, body.phone, body.plan, body.status, body.start_date, body.notes, now))
        return _get("members", int(cur.lastrowid))


@app.put("/api/business/members/{item_id}")
def members_update(item_id: int, body: MemberIn, user=Depends(require_user)):
    with database.db() as conn:
        cur = conn.execute("UPDATE members SET name=?, phone=?, plan=?, status=?, start_date=?, notes=? WHERE id=?", (body.name, body.phone, body.plan, body.status, body.start_date, body.notes, item_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Not found")
    return _get("members", item_id)


@app.delete("/api/business/members/{item_id}")
def members_delete(item_id: int, user=Depends(require_user)):
    return _delete("members", item_id)


@app.get("/api/business/activities")
def activities_list(user=Depends(require_user)):
    return _list("activities")


@app.post("/api/business/activities")
def activities_create(body: ActivityIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("INSERT INTO activities (title, category, employee_name, activity_date, notes, created_at) VALUES (?,?,?,?,?,?)", (body.title, body.category, body.employee_name, body.activity_date or date.today().isoformat(), body.notes, now))
        return _get("activities", int(cur.lastrowid))


@app.put("/api/business/activities/{item_id}")
def activities_update(item_id: int, body: ActivityIn, user=Depends(require_user)):
    with database.db() as conn:
        cur = conn.execute("UPDATE activities SET title=?, category=?, employee_name=?, activity_date=?, notes=? WHERE id=?", (body.title, body.category, body.employee_name, body.activity_date or date.today().isoformat(), body.notes, item_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Not found")
    return _get("activities", item_id)


@app.delete("/api/business/activities/{item_id}")
def activities_delete(item_id: int, user=Depends(require_user)):
    return _delete("activities", item_id)


@app.get("/api/customers")
def customers_list(user=Depends(require_user)):
    return _list("customers")


@app.post("/api/customers")
def customers_create(body: CustomerIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("INSERT INTO customers (business_name, contact_name, phone, email, address, city, state, kind, status, notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (body.business_name, body.contact_name, body.phone, body.email, body.address, body.city, body.state, body.kind, body.status, body.notes, now, now))
        return _get("customers", int(cur.lastrowid))


@app.put("/api/customers/{item_id}")
def customers_update(item_id: int, body: CustomerIn, user=Depends(require_user)):
    now = datetime.utcnow().isoformat()
    with database.db() as conn:
        cur = conn.execute("UPDATE customers SET business_name=?, contact_name=?, phone=?, email=?, address=?, city=?, state=?, kind=?, status=?, notes=?, updated_at=? WHERE id=?", (body.business_name, body.contact_name, body.phone, body.email, body.address, body.city, body.state, body.kind, body.status, body.notes, now, item_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Not found")
    return _get("customers", item_id)


@app.delete("/api/customers/{item_id}")
def customers_delete(item_id: int, user=Depends(require_user)):
    return _delete("customers", item_id)


@app.get("/api/print/summary")
def print_summary(user=Depends(require_user)):
    with database.db() as conn:
        return {
            "employees": database.rows_to_list(conn.execute("SELECT id, name, role, status FROM employees ORDER BY name").fetchall()),
            "tasks": database.rows_to_list(conn.execute("SELECT id, title, assignee, status, due_date FROM tasks ORDER BY id DESC LIMIT 100").fetchall()),
            "orders": database.rows_to_list(conn.execute("SELECT id, customer_name, item, amount, status, order_date FROM orders ORDER BY id DESC LIMIT 100").fetchall()),
            "members": database.rows_to_list(conn.execute("SELECT id, name, plan, status FROM members ORDER BY name").fetchall()),
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }


@app.get("/api/settings")
def settings(user=Depends(require_user)):
    return {"user": {"username": user["username"], "display_name": user["display_name"], "role": user["role"], "is_customer": is_customer_admin(user), "is_developer": is_developer(user)}, "app_version": app.version, "notes": "Independent web app. Desktop EXE is unchanged."}


@app.get("/api/backup/database")
def backup_database(user=Depends(require_user)):
    path = database.DB_PATH
    if not path.exists():
        raise HTTPException(404, "Database file not found")
    return FileResponse(path, filename="employee-audit-web-backup.db", media_type="application/octet-stream")


assets_dir = STATIC / "assets"
if assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/")
def spa_root():
    index = STATIC / "index.html"
    if not index.exists():
        return JSONResponse({"error": "SPA not built"}, status_code=500)
    return FileResponse(index)


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(404, "API route not found")
    candidate = (STATIC / full_path).resolve()
    try:
        candidate.relative_to(STATIC.resolve())
    except ValueError:
        raise HTTPException(404, "Not found")
    if candidate.is_file():
        return FileResponse(candidate)
    index = STATIC / "index.html"
    if index.exists():
        return FileResponse(index)
    raise HTTPException(404, "Not found")
