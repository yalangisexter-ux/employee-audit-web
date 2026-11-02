"""SQLite persistence for the independent Employee Audit web app."""
from __future__ import annotations

import os
import sqlite3
import hashlib
import secrets
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

DATA_DIR = Path(os.environ.get("AUDIT_DATA_DIR") or Path(__file__).resolve().parent.parent / "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "employee_audit_web.db"

PBKDF2_ITERATIONS = 310_000

# Predefined production bootstrap accounts (case-sensitive usernames).
DEFAULT_ADMIN_USERNAME = "Admin"
DEFAULT_ADMIN_PASSWORD = "Shiva@01"
DEFAULT_DEV_USERNAME = "admin"
DEFAULT_DEV_PASSWORD = "kiran123"
DEFAULT_DEV_PASSWORD_ALT = "Devlopershouse@1996#"


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        algo, iters, salt, digest = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        check = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iters)
        ).hex()
        return secrets.compare_digest(check, digest)
    except Exception:
        return False


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL COLLATE BINARY,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Admin',
    password_hash TEXT NOT NULL,
    password_hash_alt TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE BINARY);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    email TEXT DEFAULT '',
    status TEXT DEFAULT 'Active',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    assignee TEXT DEFAULT '',
    status TEXT DEFAULT 'Open',
    priority TEXT DEFAULT 'Normal',
    due_date TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    employee_name TEXT NOT NULL,
    work_date TEXT NOT NULL,
    status TEXT DEFAULT 'Present',
    check_in TEXT DEFAULT '',
    check_out TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(employee_name, work_date)
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku TEXT DEFAULT '',
    category TEXT DEFAULT '',
    stock INTEGER DEFAULT 0,
    price REAL DEFAULT 0,
    notes TEXT DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT DEFAULT '',
    price REAL DEFAULT 0,
    duration_min INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    item TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    amount REAL DEFAULT 0,
    status TEXT DEFAULT 'Pending',
    order_date TEXT NOT NULL,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT DEFAULT '',
    plan TEXT DEFAULT '',
    status TEXT DEFAULT 'Active',
    start_date TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name TEXT NOT NULL,
    contact_name TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    email TEXT DEFAULT '',
    address TEXT DEFAULT '',
    city TEXT DEFAULT '',
    state TEXT DEFAULT '',
    kind TEXT DEFAULT 'Prospect',
    status TEXT DEFAULT 'New',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT DEFAULT '',
    employee_name TEXT DEFAULT '',
    activity_date TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _upsert_user(
    conn: sqlite3.Connection,
    username: str,
    display_name: str,
    role: str,
    password: str,
    password_alt: str | None = None,
    force_password: bool = False,
) -> None:
    now = datetime.utcnow().isoformat()
    row = conn.execute(
        "SELECT id, password_hash, password_hash_alt FROM users WHERE username = ? COLLATE BINARY",
        (username,),
    ).fetchone()
    password_hash = hash_password(password)
    alt_hash = hash_password(password_alt) if password_alt else None
    if row is None:
        conn.execute(
            "INSERT INTO users (username, display_name, role, password_hash, password_hash_alt, is_active, created_at) VALUES (?,?,?,?,?,1,?)",
            (username, display_name, role, password_hash, alt_hash, now),
        )
        return
    if force_password:
        conn.execute(
            "UPDATE users SET display_name=?, role=?, password_hash=?, password_hash_alt=?, is_active=1 WHERE id=?",
            (display_name, role, password_hash, alt_hash, row["id"]),
        )
        return
    # Keep existing hashes unless force requested; still refresh display metadata.
    conn.execute(
        "UPDATE users SET display_name=?, role=?, is_active=1 WHERE id=?",
        (display_name, role, row["id"]),
    )


def _seed_default_accounts(conn: sqlite3.Connection) -> None:
    """Ensure the known Admin/admin accounts exist for first login."""
    # Env overrides still supported for hosted secrets.
    admin_username = os.environ.get("WEB_ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME).strip() or DEFAULT_ADMIN_USERNAME
    admin_password = os.environ.get("WEB_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD) or DEFAULT_ADMIN_PASSWORD
    admin_display = os.environ.get("WEB_ADMIN_DISPLAY_NAME", "Taruna (Customer)").strip() or "Taruna (Customer)"

    dev_username = os.environ.get("WEB_DEVELOPER_USERNAME", DEFAULT_DEV_USERNAME).strip() or DEFAULT_DEV_USERNAME
    dev_password = os.environ.get("WEB_DEVELOPER_PASSWORD", DEFAULT_DEV_PASSWORD) or DEFAULT_DEV_PASSWORD
    dev_password_alt = os.environ.get("WEB_DEVELOPER_PASSWORD_ALT", DEFAULT_DEV_PASSWORD_ALT) or DEFAULT_DEV_PASSWORD_ALT

    # Always ensure predefined accounts exist. force_password only when no users yet
    # or WEB_FORCE_BOOTSTRAP_PASSWORDS=1 so restarts do not reset operator changes.
    user_count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    force = user_count == 0 or os.environ.get("WEB_FORCE_BOOTSTRAP_PASSWORDS", "0").strip().lower() in ("1", "true", "yes")

    _upsert_user(conn, admin_username, admin_display, "Admin", admin_password, force_password=force)
    if dev_username != admin_username:
        _upsert_user(
            conn,
            dev_username,
            "Developer",
            "Developer",
            dev_password,
            password_alt=dev_password_alt,
            force_password=force,
        )


def init_db() -> None:
    with db() as conn:
        conn.executescript(SCHEMA)
        # Default ON so Light Cloud / first deploy has a working Admin login.
        # Set WEB_BOOTSTRAP_USERS=0 to skip seeding entirely.
        bootstrap_flag = os.environ.get("WEB_BOOTSTRAP_USERS", "1").strip().lower()
        if bootstrap_flag not in ("0", "false", "no", "off"):
            try:
                _seed_default_accounts(conn)
            except Exception as exc:
                print(f"Bootstrap warning: {exc}")
        conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', '3')")


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [row_to_dict(r) for r in rows]  # type: ignore
