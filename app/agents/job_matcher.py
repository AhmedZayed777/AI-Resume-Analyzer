from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .llm import get_llm
from .schemas import JobInput, JobMatch, ResumeAnalysis

ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "postgres": "postgresql",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "sklearn": "scikit-learn",
    "k8s": "kubernetes",
    "fast api": "fastapi",
}

SKILL_WEIGHT = 0.75
EXPERIENCE_WEIGHT = 0.25


def _norm(skill: str) -> str:
    s = skill.strip().lower()
    return ALIASES.get(s, s)


def _score(resume: ResumeAnalysis, job: JobInput) -> JobMatch:
    resume_skills = {_norm(s) for s in resume.technical_skills}
    required = {_norm(s): s for s in job.required_skills}

    matched = [orig for norm, orig in required.items() if norm in resume_skills]
    missing = [orig for norm, orig in required.items() if norm not in resume_skills]

    skill_ratio = len(matched) / len(required) if required else 1.0
    if job.min_years_experience > 0:
        exp_ratio = min(resume.years_of_experience / job.min_years_experience, 1.0)
    else:
        exp_ratio = 1.0

    score = round(100 * (SKILL_WEIGHT * skill_ratio + EXPERIENCE_WEIGHT * exp_ratio), 1)
    return JobMatch(
        job_id=job.id,
        title=job.title,
        score=score,
        matched_skills=matched,
        missing_skills=missing,
    )


_explain_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a career coach. In 3-4 sentences explain to the candidate why this job scored as it did. "
            "Mention the strongest matches, the most important gaps, and one concrete next step. "
            "Base everything strictly on the data provided.",
        ),
        (
            "human",
            "Candidate summary: {summary}\n"
            "Candidate experience: {years} years\n\n"
            "Job: {title}\n{description}\n\n"
            "Match score: {score}/100\n"
            "Matched skills: {matched}\n"
            "Missing skills: {missing}",
        ),
    ]
)


def match_jobs(
    resume: ResumeAnalysis,
    jobs: list[JobInput],
    top_k: int = 5,
    min_score: float = 0.0,
) -> list[JobMatch]:
    matches = [_score(resume, job) for job in jobs]
    matches = [m for m in matches if m.score >= min_score]
    matches.sort(key=lambda m: m.score, reverse=True)
    top = matches[:top_k]
    if not top:
        return []

    jobs_by_id = {j.id: j for j in jobs}
    payloads = [
        {
            "summary": resume.summary,
            "years": resume.years_of_experience,
            "title": m.title,
            "description": jobs_by_id[m.job_id].description[:1500],
            "score": m.score,
            "matched": ", ".join(m.matched_skills) or "none",
            "missing": ", ".join(m.missing_skills) or "none",
        }
        for m in top
    ]
    try:
        chain = _explain_prompt | get_llm() | StrOutputParser()
        explanations = chain.batch(payloads)
    except Exception:
        explanations = None
    for match, text in zip(top, explanations or []):
        match.explanation = (text or "").strip()
    for match in top:
        if not match.explanation:
            match.explanation = (
                f"Score {match.score}/100 from matched skills "
                f"({', '.join(match.matched_skills) or 'none'}) and experience fit. "
                f"Missing: {', '.join(match.missing_skills) or 'none'}."
            )
    return top