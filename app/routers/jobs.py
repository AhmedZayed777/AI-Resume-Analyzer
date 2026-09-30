import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import db as dbm
from ..security import get_current_user

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    company: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    required_skills: list[str] = Field(default_factory=list, max_length=30)
    min_years_experience: float = Field(default=0, ge=0, le=50)


def _get_owned_job(conn, job_id: int, user: dict):
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if row["created_by"] != user["id"]:
        raise HTTPException(status_code=403, detail="You can only modify jobs you created.")
    return row


@router.get("")
def list_jobs(
    q: str | None = None,
    location: str | None = None,
    skill: str | None = None,
    user: dict = Depends(get_current_user),
) -> list[dict]:
    sql = "SELECT * FROM jobs WHERE 1=1"
    params: list = []
    if q:
        sql += " AND (LOWER(title) LIKE ? OR LOWER(company) LIKE ? OR LOWER(description) LIKE ?)"
        like = f"%{q.strip().lower()}%"
        params += [like, like, like]
    if location:
        sql += " AND LOWER(location) LIKE ?"
        params.append(f"%{location.strip().lower()}%")
    if skill:
        sql += " AND LOWER(required_skills) LIKE ?"
        params.append(f"%{skill.strip().lower()}%")
    sql += " ORDER BY id"
    with dbm.get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dbm.row_to_job(r) for r in rows]


@router.post("", status_code=201)
def create_job(payload: JobIn, user: dict = Depends(get_current_user)) -> dict:
    with dbm.get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO jobs (title, company, location, description, required_skills,"
            " min_years_experience, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                payload.title.strip(), payload.company.strip(), payload.location.strip(),
                payload.description.strip(),
                json.dumps([s.strip() for s in payload.required_skills if s.strip()]),
                payload.min_years_experience, user["id"],
            ),
        )
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dbm.row_to_job(row)


@router.get("/{job_id}")
def get_job(job_id: int, user: dict = Depends(get_current_user)) -> dict:
    with dbm.get_db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return dbm.row_to_job(row)


@router.put("/{job_id}")
def update_job(job_id: int, payload: JobIn, user: dict = Depends(get_current_user)) -> dict:
    with dbm.get_db() as conn:
        _get_owned_job(conn, job_id, user)
        conn.execute(
            "UPDATE jobs SET title = ?, company = ?, location = ?, description = ?,"
            " required_skills = ?, min_years_experience = ?, updated_at = datetime('now')"
            " WHERE id = ?",
            (
                payload.title.strip(), payload.company.strip(), payload.location.strip(),
                payload.description.strip(),
                json.dumps([s.strip() for s in payload.required_skills if s.strip()]),
                payload.min_years_experience, job_id,
            ),
        )
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dbm.row_to_job(row)


@router.delete("/{job_id}")
def delete_job(job_id: int, user: dict = Depends(get_current_user)) -> dict:
    with dbm.get_db() as conn:
        _get_owned_job(conn, job_id, user)
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    return {"ok": True}
