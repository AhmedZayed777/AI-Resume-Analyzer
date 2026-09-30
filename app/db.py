import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import DB_PATH

SEED_JOBS = [
    {"title": "Junior Backend Developer", "company": "Tech Solutions", "location": "Cairo, Egypt",
     "description": "Build and maintain REST APIs with Python and FastAPI. Work with SQL databases, write tests, and containerize services with Docker.",
     "required_skills": ["Python", "FastAPI", "SQL", "Docker"], "min_years_experience": 1},
    {"title": "Mid Backend Engineer", "company": "Nile Software House", "location": "Remote",
     "description": "Design scalable backend services, own database schemas, and improve API performance for a SaaS product.",
     "required_skills": ["Python", "Django", "PostgreSQL", "Kubernetes"], "min_years_experience": 3},
    {"title": "Frontend Developer", "company": "Pixel Agency", "location": "Giza, Egypt",
     "description": "Implement responsive, accessible interfaces from designs. Collaborate with designers and backend engineers on a component library.",
     "required_skills": ["JavaScript", "HTML", "CSS", "React"], "min_years_experience": 2},
    {"title": "Machine Learning Engineer", "company": "DataWorks", "location": "Remote",
     "description": "Train and evaluate models, build data pipelines, and deploy predictions to production endpoints.",
     "required_skills": ["Python", "scikit-learn", "Pandas", "Docker", "SQL"], "min_years_experience": 2},
    {"title": "Data Analyst", "company": "Retail Group", "location": "Cairo, Egypt",
     "description": "Turn sales data into dashboards and reports, clean datasets, and support stakeholders with ad-hoc analysis.",
     "required_skills": ["SQL", "Pandas", "Excel", "Tableau"], "min_years_experience": 1},
    {"title": "AI Engineer", "company": "Startup Lab", "location": "Remote",
     "description": "Integrate LLM APIs into product features, build RAG pipelines, and evaluate prompt and retrieval quality.",
     "required_skills": ["Python", "LLM APIs", "RAG", "LangChain", "Vector databases"], "min_years_experience": 2},
    {"title": "Junior DevOps Engineer", "company": "CloudNine", "location": "Alexandria, Egypt (Hybrid)",
     "description": "Maintain CI/CD pipelines, containerize applications, and monitor cloud infrastructure.",
     "required_skills": ["Docker", "Linux", "Bash", "CI/CD", "AWS"], "min_years_experience": 1},
    {"title": "QA Automation Engineer", "company": "Quality First", "location": "Cairo, Egypt",
     "description": "Write automated tests for web and API features, maintain test suites, and report bugs clearly.",
     "required_skills": ["Python", "Pytest", "Selenium", "API testing"], "min_years_experience": 1},
]

SEED_KNOWLEDGE = [
    ("roadmap", "Backend Developer roadmap",
     "learn Python, FastAPI, SQL, REST design, authentication with JWT, Docker, testing with pytest, then CI/CD and cloud basics."),
    ("roadmap", "Data Scientist roadmap",
     "Python, pandas, NumPy, statistics, scikit-learn, feature engineering, model evaluation, then deep learning and MLOps."),
    ("roadmap", "AI Engineer roadmap",
     "Python, LLM APIs, prompt engineering, LangChain, vector databases, RAG, evaluation, and deployment of AI services."),
    ("roadmap", "Frontend Developer roadmap",
     "HTML, CSS, JavaScript, DOM, fetch API, accessibility, responsive design, then a framework and build tools."),
    ("certification", "Certifications",
     "AWS Certified Cloud Practitioner for cloud basics; Google Data Analytics Certificate for analytics; TensorFlow Developer Certificate for deep learning; Microsoft Azure AI Fundamentals AI-900 for applied AI."),
    ("resource", "Learning resources",
     "freeCodeCamp for web development, Coursera Machine Learning Specialization for ML, DeepLearning.AI short courses for LLMs, official FastAPI documentation for backend APIs, LangChain documentation for agents."),
    ("guideline", "Resume writing guidelines",
     "keep it to one page for under ten years of experience, lead bullets with action verbs, quantify results, list skills grouped by category, tailor keywords to the job description, avoid photos and dense paragraphs."),
    ("skill", "Skill description SQL",
     "querying relational databases, joins, aggregation, indexing and schema design. Required for most backend and data roles."),
    ("skill", "Skill description Docker",
     "packaging applications into containers for reproducible deployment. Expected for backend, DevOps and MLOps roles."),
    ("skill", "Skill description REST APIs",
     "designing stateless HTTP endpoints with correct status codes, validation, pagination and versioning. Core requirement for backend roles."),
    ("skill", "Skill description Git",
     "branching, pull requests, meaningful commits and conflict resolution. Expected in every software team."),
    ("skill", "Soft skills employers value",
     "communication, teamwork, problem solving, time management, adaptability and ownership of tasks."),
    ("job_description", "Backend developer job description sample",
     "responsible for designing and implementing server-side logic, managing databases, integrating third-party services, and ensuring API reliability, security and performance."),
    ("job_description", "Machine learning engineer job description sample",
     "responsible for data preparation, model training and evaluation, experiment tracking, and deploying models behind APIs with monitoring."),
    ("job_description", "Frontend developer job description sample",
     "responsible for building responsive user interfaces, implementing designs faithfully, optimizing page performance, and ensuring accessibility."),
    ("guideline", "How to tailor a resume to a job description",
     "mirror the exact skill names used in the posting, put the most relevant projects first, and move matching keywords into a visible skills section."),
]


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    from .security import hash_password

    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    with get_db() as conn:
        conn.executescript(schema)
        if conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] == 0:
            conn.execute(
                "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?)",
                ("demo@example.com", hash_password("demo12345"), "Demo User"),
            )
        if conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"] == 0:
            demo_id = conn.execute(
                "SELECT id FROM users WHERE email = ?", ("demo@example.com",)
            ).fetchone()["id"]
            for job in SEED_JOBS:
                conn.execute(
                    "INSERT INTO jobs (title, company, location, description, required_skills,"
                    " min_years_experience, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        job["title"], job["company"], job["location"], job["description"],
                        json.dumps(job["required_skills"]), job["min_years_experience"], demo_id,
                    ),
                )
        if conn.execute("SELECT COUNT(*) AS c FROM knowledge").fetchone()["c"] == 0:
            for category, title, content in SEED_KNOWLEDGE:
                conn.execute(
                    "INSERT INTO knowledge (category, title, content) VALUES (?, ?, ?)",
                    (category, title, content),
                )


def row_to_job(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "company": row["company"],
        "location": row["location"],
        "description": row["description"],
        "required_skills": json.loads(row["required_skills"]),
        "min_years_experience": row["min_years_experience"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
