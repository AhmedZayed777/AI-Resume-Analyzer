from langchain_core.prompts import ChatPromptTemplate

from .llm import call_with_retry, get_llm
from .schemas import ResumeAnalysis

MAX_CHARS = 12000

_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert technical recruiter. Extract structured data from the resume text. "
            "Only use information present in the resume; never invent skills, employers or dates. "
            "Separate technical skills (languages, frameworks, tools) from soft skills. "
            "Estimate total years of professional experience from the dates given, 0 if none. "
            "Write a 3-4 sentence professional summary. "
            "List concrete strengths and weaknesses (for example missing metrics, thin experience, vague bullets).",
        ),
        ("human", "Resume text:\n\n{resume_text}"),
    ]
)


def analyze_resume(resume_text: str) -> ResumeAnalysis:
    text = (resume_text or "").strip()
    if len(text) < 50:
        raise ValueError("Resume text is empty or too short to analyze")
    chain = _prompt | get_llm().with_structured_output(ResumeAnalysis)
    return call_with_retry(lambda: chain.invoke({"resume_text": text[:MAX_CHARS]}))