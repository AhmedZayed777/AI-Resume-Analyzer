from app.agents import analyze_resume, ask_advisor, improve_resume, match_jobs
from app.agents.schemas import JobInput

RESUME = """
Ahmed Ali | ahmed@example.com
Computer Science student, Benha University, expected graduation 2027.
Skills: Python, FastAPI, SQL, Git, Pandas, scikit-learn, teamwork, communication.
Projects: Built a REST API for a task manager with FastAPI and SQLite.
Trained a churn prediction model with scikit-learn reaching 84% accuracy.
Internship: Junior Python Developer at TechCo, 3 months, wrote unit tests and fixed bugs.
"""

JOBS = [
    JobInput(
        id=1,
        title="Junior Backend Developer",
        description="Build and maintain REST APIs with Python and FastAPI. Work with SQL databases and Docker.",
        required_skills=["Python", "FastAPI", "SQL", "Docker"],
        min_years_experience=1,
    ),
    JobInput(
        id=2,
        title="Frontend Developer",
        description="Build responsive interfaces with JavaScript and CSS.",
        required_skills=["JavaScript", "HTML", "CSS", "React"],
        min_years_experience=2,
    ),
    JobInput(
        id=3,
        title="Machine Learning Engineer",
        description="Train and deploy ML models, build data pipelines.",
        required_skills=["Python", "scikit-learn", "Pandas", "Docker", "SQL"],
        min_years_experience=1,
    ),
]

if __name__ == "__main__":
    analysis = analyze_resume(RESUME)
    print(analysis.model_dump_json(indent=2))

    for m in match_jobs(analysis, JOBS):
        print(f"\n{m.title}: {m.score}\n{m.explanation}")

    plan = improve_resume(analysis, "Backend Developer")
    print(plan.model_dump_json(indent=2))

    print(ask_advisor("What should I learn next to get a backend job?", analysis))