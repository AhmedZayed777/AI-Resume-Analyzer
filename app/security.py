import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, HTTPException

from .config import SESSION_TTL_DAYS


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, expected = stored.split("$")
    except (ValueError, AttributeError):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000)
    return secrets.compare_digest(dk.hex(), expected)


def create_session(conn, user_id: int) -> str:
    token = secrets.token_hex(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires.strftime("%Y-%m-%d %H:%M:%S")),
    )
    return token


def delete_session(conn, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def get_current_user(sid: str | None = Cookie(default=None, alias="sid")) -> dict:
    if not sid:
        raise HTTPException(status_code=401, detail="Not logged in")
    from .db import get_db

    with get_db() as conn:
        row = conn.execute(
            "SELECT u.id, u.email, u.full_name FROM sessions s"
            " JOIN users u ON u.id = s.user_id"
            " WHERE s.token = ? AND s.expires_at > datetime('now')",
            (sid,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return {"id": row["id"], "email": row["email"], "full_name": row["full_name"]}
