import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import db as dbm
from ..agents import ask_advisor
from ..agents.llm import describe_ai_error
from ..agents.schemas import Education, Experience, ResumeAnalysis
from ..security import get_current_user

router = APIRouter(prefix="/api/advisor", tags=["advisor"])

AI_DOWN = "The AI advisor is unavailable right now. Check LLM_API_KEY and LLM_BASE_URL in .env and try again."


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    resume_id: int | None = None
    history: list[HistoryItem] = Field(default_factory=list, max_length=20)


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


@router.post("/ask")
def ask(payload: AskIn, user: dict = Depends(get_current_user)) -> dict:
    analysis = None
    if payload.resume_id is not None:
        with dbm.get_db() as conn:
            row = conn.execute(
                "SELECT r.user_id, a.* FROM resumes r LEFT JOIN analyses a ON a.resume_id = r.id"
                " WHERE r.id = ?",
                (payload.resume_id,),
            ).fetchone()
        if row is None or row["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Resume not found.")
        if row["years_experience"] is not None:
            analysis = _analysis_from_row(row)
    try:
        answer = ask_advisor(
            payload.question,
            analysis,
            [h.model_dump() for h in payload.history],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=describe_ai_error(exc, AI_DOWN)) from exc
    return {"answer": answer}
