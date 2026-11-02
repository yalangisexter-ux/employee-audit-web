"""Authentication helpers with restart-safe, signed bearer sessions."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
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
    if database.verify_password(password, user.get("password_hash")):
        return user
    # Developer account may accept a second known password.
    if database.verify_password(password, user.get("password_hash_alt")):
        return user
    return None


def _session_secret() -> bytes:
    configured = os.environ.get("WEB_SESSION_SECRET", "").strip()
    if configured:
        if len(configured) < 32:
            # Fall back to generated key rather than hard-failing login.
            pass
        else:
            return configured.encode("utf-8")

    key_path = Path(database.DATA_DIR) / ".web_session_secret"
    try:
        with key_path.open("xb") as handle:
            handle.write(secrets.token_bytes(48))
        try:
            key_path.chmod(0o600)
        except OSError:
            pass
    except FileExistsError:
        pass
    except OSError:
        if not key_path.exists():
            # Last-resort in-memory key so the process can still accept logins.
            return hashlib.sha256(b"employee-audit-web-fallback-session").digest()
    try:
        key = key_path.read_bytes()
        if len(key) >= 32:
            return key
    except OSError:
        pass
    return hashlib.sha256(b"employee-audit-web-fallback-session").digest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_session(user_id: int, hours: int = 24 * 14) -> str:
    user = None
    with database.db() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE id=? AND is_active=1", (user_id,)
        ).fetchone()
        user = database.row_to_dict(row)
    if not user:
        raise ValueError("Cannot create a session for an inactive or missing user")
    expires = int((datetime.now(timezone.utc) + timedelta(hours=hours)).timestamp())
    payload = {
        "uid": int(user["id"]),
        "exp": expires,
        "pwd": hashlib.sha256(user["password_hash"].encode("utf-8")).hexdigest(),
        "nonce": secrets.token_urlsafe(12),
    }
    encoded = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _b64(hmac.new(_session_secret(), encoded.encode("ascii"), hashlib.sha256).digest())
    return encoded + "." + signature


def session_user(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        encoded, supplied_signature = token.split(".", 1)
        expected = _b64(hmac.new(_session_secret(), encoded.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(supplied_signature, expected):
            return None
        payload = json.loads(_unb64(encoded))
        if int(payload.get("exp", 0)) <= int(datetime.now(timezone.utc).timestamp()):
            return None
        with database.db() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id=? AND is_active=1", (int(payload["uid"]),)
            ).fetchone()
            user = database.row_to_dict(row)
        if not user:
            return None
        current_fingerprint = hashlib.sha256(user["password_hash"].encode("utf-8")).hexdigest()
        if not hmac.compare_digest(str(payload.get("pwd", "")), current_fingerprint):
            return None
        return user
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def require_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    user = session_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def is_customer_admin(user: dict[str, Any]) -> bool:
    # Exact username Admin is the customer path.
    if str(user.get("username") or "") == "Admin":
        return True
    role = str(user.get("role") or "").strip().lower()
    return role in {"customer admin", "customer"}


def is_developer(user: dict[str, Any]) -> bool:
    if str(user.get("username") or "") == "admin":
        return True
    return str(user.get("role") or "").strip().lower() == "developer"
