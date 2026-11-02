"""Authentication helpers — case-sensitive Admin vs admin."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any

from fastapi import Header, HTTPException

from . import db as database


def find_user(username: str) -> dict[str, Any] | None:
    with database.db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE BINARY AND is_active = 1",
            (username,),
        ).fetchone()
        return database.row_to_dict(row)


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    user = find_user(username)
    if not user:
        return None
    if database.verify_password(password, user["password_hash"]):
        return user
    alt = user.get("password_hash_alt")
    if alt and database.verify_password(password, alt):
        return user
    return None


def create_session(user_id: int, hours: int = 24 * 14) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    exp = now + timedelta(hours=hours)
    with database.db() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
            (token, user_id, now.isoformat(), exp.isoformat()),
        )
    return token


def session_user(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    with database.db() as conn:
        row = conn.execute(
            """
            SELECT u.* FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ? AND u.is_active = 1 AND s.expires_at > ?
            """,
            (token, datetime.utcnow().isoformat()),
        ).fetchone()
        return database.row_to_dict(row)


def require_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    user = session_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def is_customer_admin(user: dict[str, Any]) -> bool:
    return str(user.get("username") or "") == "Admin"


def is_developer(user: dict[str, Any]) -> bool:
    un = str(user.get("username") or "")
    role = str(user.get("role") or "").lower()
    return un == "admin" or role == "developer"
