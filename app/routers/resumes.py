import json
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .. import config, db as dbm
from ..agents import analyze_resume, improve_resume, match_jobs
from ..agents.llm import describe_ai_error
from ..agents.schemas import Education, Experience, JobInput, ResumeAnalysis
from ..security import get_current_user
from ..services.extraction import ExtractionError, extract_text

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

logger = logging.getLogger("uvicorn.error")

AI_DOWN = "AI analysis is unavailable right now. Check LLM_API_KEY and LLM_BASE_URL in .env and try again."


class ImproveIn(BaseModel):
    target_role: str = Field(min_length=2, max_length=120)


def _analysis_to_dict(a: ResumeAnalysis) -> dict:
    return a.model_dump()


def _analysis_from_row(row) -> ResumeAnalysis:
    return ResumeAnalysis(
        full_name=row["full_name"],
        email=row["email"],
        technical_skills=json.loads(row["technical_skills"]),
        soft_skills=json.loads(row["soft_skills"]),
        education=[Education(**e) for e in json.loads(row["education"])],
        experience=[Experience(**e) for e in json.loads(row["experience"])],
        years_of_experience=row["years_experience"],
        summary=row["summary"],
        strengths=json.loads(row["strengths"]),
        weaknesses=json.loads(row["weaknesses"]),
    )


def _save_analysis(conn, resume_id: int, a: ResumeAnalysis) -> None:
    conn.execute(
        "INSERT INTO analyses (resume_id, full_name, email, years_experience, summary,"
        " technical_skills, soft_skills, education, experience, strengths, weaknesses)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            resume_id, a.full_name, a.email, a.years_of_experience, a.summary,
            json.dumps(a.technical_skills), json.dumps(a.soft_skills),
            json.dumps([e.model_dump() for e in a.education]),
            json.dumps([e.model_dump() for e in a.experience]),
            json.dumps(a.strengths), json.dumps(a.weaknesses),
        ),
    )


def _load_owned_resume(conn, resume_id: int, user: dict):
    row = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
    if row is None or row["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return row


@router.post("", status_code=201)
async def upload_resume(file: UploadFile = File(...), user: dict = Depends(get_current_user)) -> dict:
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File is too large (max 5 MB).")
    if not data:
        raise HTTPException(status_code=400, detail="No file received.")
    try:
        text = extract_text(file.filename or "", data)
    except ExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with dbm.get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO resumes (user_id, filename, raw_text) VALUES (?, ?, ?)",
            (user["id"], file.filename, text),
        )
        resume_id = cursor.lastrowid

    try:
        analysis = analyze_resume(text)
    except Exception as exc:
        logger.exception("analyze_resume failed for resume %s", resume_id)
        raise HTTPException(status_code=502, detail=describe_ai_error(exc, AI_DOWN)) from exc

    with dbm.get_db() as conn:
        _save_analysis(conn, resume_id, analysis)
        job_rows = conn.execute("SELECT * FROM jobs").fetchall()
    jobs = [
        JobInput(
            id=r["id"], title=r["title"], description=r["description"],
            required_skills=json.loads(r["required_skills"]),
            min_years_experience=r["min_years_experience"],
        )
        for r in job_rows
    ]
    try:
        matches = match_jobs(analysis, jobs, top_k=5)
    except Exception:
        matches = []
    if matches:
        with dbm.get_db() as conn:
            for m in matches:
                conn.execute(
                    "INSERT INTO matches (resume_id, job_id, score, matched_skills,"
                    " missing_skills, explanation) VALUES (?, ?, ?, ?, ?, ?)",
                    (resume_id, m.job_id, m.score, json.dumps(m.matched_skills),
                     json.dumps(m.missing_skills), m.explanation),
                )
    return {"resume_id": resume_id, "analysis": _analysis_to_dict(analysis)}


@router.get("")
def list_resumes(user: dict = Depends(get_current_user)) -> list[dict]:
    with dbm.get_db() as conn:
        rows = conn.execute(
            "SELECT r.id, r.filename, r.uploaded_at, a.summary, a.full_name"
            " FROM resumes r LEFT JOIN analyses a ON a.resume_id = r.id"
            " WHERE r.user_id = ? ORDER BY r.id DESC",
            (user["id"],),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{resume_id}")
def get_resume(resume_id: int, user: dict = Depends(get_current_user)) -> dict:
    with dbm.get_db() as conn:
        row = _load_owned_resume(conn, resume_id, user)
        arow = conn.execute("SELECT * FROM analyses WHERE resume_id = ?", (resume_id,)).fetchone()
    return {
        "id": row["id"],
        "filename": row["filename"],
        "uploaded_at": row["uploaded_at"],
        "analysis": _analysis_to_dict(_analysis_from_row(arow)) if arow else None,
    }


@router.get("/{resume_id}/matches")
def get_matches(resume_id: int, user: dict = Depends(get_current_user)) -> list[dict]:
    with dbm.get_db() as conn:
        _load_owned_resume(conn, resume_id, user)
        rows = conn.execute(
            "SELECT m.job_id, m.score, m.matched_skills, m.missing_skills, m.explanation,"
            " j.title, j.company, j.location FROM matches m JOIN jobs j ON j.id = m.job_id"
            " WHERE m.resume_id = ? ORDER BY m.score DESC",
            (resume_id,),
        ).fetchall()
    return [
        {
            "job_id": r["job_id"], "title": r["title"], "company": r["company"],
            "location": r["location"], "score": r["score"],
            "matched_skills": json.loads(r["matched_skills"]),
            "missing_skills": json.loads(r["missing_skills"]),
            "explanation": r["explanation"],
        }
        for r in rows
    ]


@router.post("/{resume_id}/improve")
def improve(resume_id: int, payload: ImproveIn, user: dict = Depends(get_current_user)) -> dict:
    with dbm.get_db() as conn:
        _load_owned_resume(conn, resume_id, user)
        arow = conn.execute("SELECT * FROM analyses WHERE resume_id = ?", (resume_id,)).fetchone()
    if arow is None:
        raise HTTPException(status_code=400, detail="No analysis found for this resume.")
    analysis = _analysis_from_row(arow)
    try:
        plan = improve_resume(analysis, payload.target_role.strip())
    except Exception as exc:
        logger.exception("improve_resume failed for resume %s", resume_id)
        raise HTTPException(status_code=502, detail=describe_ai_error(exc, AI_DOWN)) from exc
    return plan.model_dump()
