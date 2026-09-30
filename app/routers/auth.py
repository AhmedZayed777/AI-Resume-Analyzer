import re

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from .. import config, db as dbm
from ..security import (
    create_session,
    delete_session,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterIn(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(default="", max_length=120)


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="sid", value=token, httponly=True, samesite="lax",
        max_age=config.SESSION_TTL_DAYS * 86400, path="/",
    )


@router.post("/register", status_code=201)
def register(payload: RegisterIn, response: Response) -> dict:
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    with dbm.get_db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?)",
            (email, hash_password(payload.password), payload.full_name.strip()),
        )
        user_id = cursor.lastrowid
        token = create_session(conn, user_id)
    _set_cookie(response, token)
    return {"id": user_id, "email": email, "full_name": payload.full_name.strip()}


@router.post("/login")
def login(payload: LoginIn, response: Response) -> dict:
    with dbm.get_db() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, full_name FROM users WHERE email = ?",
            (payload.email.strip().lower(),),
        ).fetchone()
        if row is None or not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        token = create_session(conn, row["id"])
    _set_cookie(response, token)
    return {"id": row["id"], "email": row["email"], "full_name": row["full_name"]}


@router.post("/logout")
def logout(response: Response, sid: str | None = Cookie(default=None, alias="sid")) -> dict:
    if sid:
        with dbm.get_db() as conn:
            delete_session(conn, sid)
    response.delete_cookie("sid", path="/")
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    return user
