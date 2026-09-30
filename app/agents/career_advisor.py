from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from .knowledge import retrieve
from .llm import call_with_retry, get_llm
from .schemas import ResumeAnalysis, ResumeImprovement


@tool
def search_knowledge_base(query: str) -> str:
    """Search the career knowledge base for roadmaps, skill descriptions, certifications,
    learning resources and resume writing guidelines. Use short keyword queries."""
    docs = retrieve(query, k=4)
    if not docs:
        return "No relevant documents found."
    return "\n\n".join(f"[{i + 1}] {d}" for i, d in enumerate(docs))


_ADVISOR_PROMPT = (
    "You are a career advisor for job seekers in tech. "
    "Always call search_knowledge_base before recommending courses, certifications, roadmaps or resume advice, "
    "and ground your answer in what it returns. "
    "If the knowledge base has nothing relevant, say so and answer from general knowledge with a clear note. "
    "Be specific and concise. Do not invent course names or certifications."
)


def _resume_context(resume: ResumeAnalysis | None) -> str:
    if resume is None:
        return ""
    return (
        "\n\nCandidate profile:\n"
        f"Summary: {resume.summary}\n"
        f"Technical skills: {', '.join(resume.technical_skills)}\n"
        f"Soft skills: {', '.join(resume.soft_skills)}\n"
        f"Experience: {resume.years_of_experience} years\n"
        f"Weaknesses: {', '.join(resume.weaknesses)}"
    )


def ask_advisor(
    question: str,
    resume: ResumeAnalysis | None = None,
    history: list[dict] | None = None,
) -> str:
    agent = create_agent(
        model=get_llm(),
        tools=[search_knowledge_base],
        system_prompt=_ADVISOR_PROMPT + _resume_context(resume),
    )
    messages = list(history or []) + [{"role": "user", "content": question}]
    result = call_with_retry(lambda: agent.invoke({"messages": messages}), attempts=3, delay=3.0)
    return result["messages"][-1].content


_improve_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a resume coach. Using the candidate profile and the reference material, "
            "produce an improvement plan for the target role. Missing skills must be relevant to the role "
            "and absent from the candidate's skills. Certifications and learning resources must come "
            "from the reference material when possible.",
        ),
        (
            "human",
            "Target role: {role}\n\n"
            "Candidate skills: {skills}\n"
            "Candidate weaknesses: {weaknesses}\n"
            "Candidate summary: {summary}\n\n"
            "Reference material:\n{context}",
        ),
    ]
)


def improve_resume(resume: ResumeAnalysis, target_role: str) -> ResumeImprovement:
    query = f"{target_role} roadmap skills certifications learning resources resume guidelines"
    context = "\n".join(retrieve(query, k=6)) or "No reference material available."
    chain = _improve_prompt | get_llm().with_structured_output(ResumeImprovement)
    return call_with_retry(
        lambda: chain.invoke(
            {
                "role": target_role,
                "skills": ", ".join(resume.technical_skills),
                "weaknesses": ", ".join(resume.weaknesses),
                "summary": resume.summary,
                "context": context,
            }
        )
    )