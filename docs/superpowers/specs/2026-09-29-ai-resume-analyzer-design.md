# AI Resume Analyzer — Design Spec

**Date:** 2026-09-29
**Source:** SRS "AI Resume Analyzer" (AI_Resume_Analyzer.pdf), status: approved design

## 1. Intent and success criteria

Complete the partially-built project into a fully working web application that satisfies
every SRS requirement: FastAPI + SQLite + vanilla HTML/CSS/JS, three AI agents, RAG,
authentication, resume upload/analysis, job recommendation, resume improvement, job
management/search, plus deliverables (source, API docs, demo script, ER diagram).

Success = a grader can run two commands, log in, upload a resume, and see analysis,
job matches, improvement advice, and a RAG-grounded career answer — with all SRS
functional requirements demonstrable.

**Decisions confirmed with the user:**
- LLM: OpenRouter (free models) or any OpenAI-compatible provider, configured via `.env`
- Auth: server-side session cookie (not JWT)
- DB: auto-seed jobs + knowledge base + demo user on first run
  (demo user `demo@example.com` / `demo12345`; seeded jobs owned by the demo user,
  so edit/delete works after logging in as demo)
- Verification: manual, no automated test suite
- Architecture: Option 1 — FastAPI + stdlib `sqlite3` + JSON REST + static vanilla-JS frontend

**Constraints (SRS §2):** Python, FastAPI, SQLite, HTML/CSS/vanilla JS only. No React/Angular/Vue.

## 2. Current state (what exists, what is added)

Existing and kept:
- `app/agents/resume_analyzer.py` — LLM structured extraction → `ResumeAnalysis`
- `app/agents/job_matcher.py` — deterministic skill/experience scoring (0.75/0.25 weights) + LLM explanations
- `app/agents/career_advisor.py` — `ask_advisor` (LangChain `create_agent` with `search_knowledge_base` tool), `improve_resume` (retrieve-then-generate)
- `app/agents/knowledge.py` — keyword-scoring retrieval (to be re-backed by the `knowledge` table)
- `app/agents/schemas.py` — Pydantic models
- `demo.py` — CLI demo of the agents

Edits to existing files:
- `app/agents/init.py` → rename to `__init__.py` (currently the package exports don't load)
- `app/agents/llm.py` — read `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` from env so any
  OpenAI-compatible provider (OpenRouter preset in `.env.example`) works

New: everything else — FastAPI app, routers, DB layer, security, extraction, static frontend,
seed data, README, requirements.txt, `.env.example`.

## 3. Project structure

```
app/
  main.py            FastAPI app, static mount, routers, global exception handler
  config.py          env settings (LLM_*, SESSION_TTL, MAX_UPLOAD_BYTES)
  db.py              connection factory (WAL), init schema, auto-seed, helpers
  schema.sql         DDL for 7 tables
  security.py        PBKDF2 hash/verify, session create/validate, get_current_user dep
  routers/           auth.py, resumes.py, jobs.py, advisor.py
  services/          extraction.py (pypdf, python-docx)
  agents/            existing (renamed init, env-driven llm, DB-backed knowledge)
static/
  index.html  login.html  register.html  analyze.html  jobs.html  advisor.html
  css/style.css
  js/api.js  auth.js  analyze.js  jobs.js  advisor.js
data/app.db          created + seeded on first run (gitignored)
.env.example         LLM_API_KEY / LLM_BASE_URL / LLM_MODEL preset
requirements.txt     fastapi, uvicorn, python-multipart, pypdf, python-docx,
                     langchain, langchain-openai, python-dotenv, pydantic
README.md            run guide, API documentation, Mermaid ER diagram, demo script
docs/superpowers/specs/2026-09-29-ai-resume-analyzer-design.md   (this file)
```

## 4. Data model (SQLite, 7 tables)

- `users(id INTEGER PK, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
  full_name TEXT, created_at TEXT)` — PBKDF2-HMAC-SHA256, per-user random salt, ≥200k iterations.
- `sessions(token TEXT PK, user_id INTEGER FK→users, created_at TEXT, expires_at TEXT)` —
  cookie `sid`, httpOnly, SameSite=Lax, 7-day expiry; logout deletes the row.
- `jobs(id INTEGER PK, title, company, location, description,
  required_skills TEXT/*JSON array*/, min_years_experience REAL,
  created_by INTEGER FK→users, created_at, updated_at)`
- `resumes(id INTEGER PK, user_id FK→users, filename, raw_text, uploaded_at)`
- `analyses(id INTEGER PK, resume_id FK→resumes UNIQUE, full_name, email,
  years_experience REAL, summary, technical_skills/soft_skills/strengths/weaknesses/
  education/experience TEXT/*JSON*/, created_at)`
- `matches(id INTEGER PK, resume_id FK→resumes, job_id FK→jobs, score REAL,
  matched_skills/missing_skills TEXT/*JSON*/, explanation, created_at)` — cache of
  `match_jobs` output so re-viewing recommendations costs no LLM calls.
- `knowledge(id INTEGER PK, category, title, content)` — categories: roadmap, skill,
  certification, resource, guideline, job_description. Seeds from current `SEED_DOCS`
  plus expanded content; read by `knowledge.py` retrieval.

ER relationships: users 1→N sessions, resumes, jobs; resumes 1→1 analyses, 1→N matches;
jobs 1→N matches; knowledge standalone.

## 5. REST API

Session-protected unless noted. Errors: JSON `{"detail": "..."}` with proper status codes.

| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register` | validates email format, password ≥6 chars; 409 on duplicate |
| POST | `/api/auth/login` | 401 on bad credentials; sets `sid` cookie |
| POST | `/api/auth/logout` | deletes session, clears cookie |
| GET | `/api/auth/me` | 401 if no valid session |
| POST | `/api/resumes` | multipart PDF/DOCX, ≤5 MB → extract → `analyze_resume` → cache top-5 `match_jobs` |
| GET | `/api/resumes` | current user's resumes (+analysis summary) |
| GET | `/api/resumes/{id}` | full resume + analysis (owner only, 403/404 otherwise) |
| GET | `/api/resumes/{id}/matches` | cached recommendations with scores + explanations |
| POST | `/api/resumes/{id}/improve` | `{target_role}` → `improve_resume()` plan |
| GET | `/api/jobs` | `?q=&location=&skill=` search across title/company/description/skills (FR-7) |
| POST | `/api/jobs` | create (auth) |
| GET | `/api/jobs/{id}` | view |
| PUT | `/api/jobs/{id}` | edit (owner only; seeded jobs belong to demo user) |
| DELETE | `/api/jobs/{id}` | delete (owner only; seeded jobs belong to demo user) |
| POST | `/api/advisor/ask` | `{question, resume_id?, history?}` → RAG answer |

## 6. Agents and RAG

- `llm.py`: `init_chat_model(LLM_MODEL, model_provider="openai", base_url=LLM_BASE_URL,
  api_key=LLM_API_KEY, temperature=0)` — works with OpenRouter or any OpenAI-compatible API.
- RAG flow (SRS §5): advisor tool `search_knowledge_base` **always retrieves before
  answering**; `improve_resume` retrieves reference material before generating.
  Retrieval = keyword-overlap scoring over `knowledge` rows (dependency-free, deterministic).
- Analysis pipeline: upload → extract text → `analyze_resume` → `match_jobs` (top 5,
  min score 0) → persist → return. LLM calls run inside FastAPI sync endpoints (threadpool).
- LLM exceptions are caught at the router level → HTTP 502 with a config-hint message;
  no stack traces leak to clients.

## 7. Frontend (multi-page, vanilla JS)

- `js/api.js`: shared `request()` wrapper — JSON, credentials:include, auto-redirect to
  login on 401, error surfacing.
- **index.html** — dashboard: recent resumes, quick actions, demo-user hint.
- **login/register** — client-side validation + server error display.
- **analyze.html** — drag-drop upload (client checks type/size), results: summary,
  skill chips, education/experience, strengths/weaknesses, recommendation cards
  (score bar, matched/missing skills, explanation), target-role improvement plan
  (missing skills, certifications, learning resources).
- **jobs.html** — search/filter bar; cards; add/edit modal; delete with confirm;
  empty/loading/error states.
- **advisor.html** — chat thread; sends selected resume id as context; typing indicator.
- One shared `style.css`; responsive layout; consistent visual language.

## 8. Error handling and validation (SRS §6)

- Pydantic request models → 422 with field errors; business rules → 400/401/403/404/409.
- Upload: extension allowlist (`.pdf`, `.docx`), size ≤ 5 MB (checked client + server),
  empty/unparseable file → 400 "Could not extract text from this file".
- Global exception handler: log traceback server-side, return `{"detail": "Internal server error"}`.
- Frontend: inline field errors, toast/banner for failures, disabled buttons while pending.

## 9. Verification (manual — user decision)

Run `uvicorn app.main:app`, then exercise end-to-end: register → wrong password rejected →
login → upload sample PDF → analysis + matches render → job create/edit/search/delete →
improve plan → advisor Q&A (grounded answer) → 401 when logged out → logout. Report actual
pass/fail results as part of the final report.

## 10. Deliverables

Complete source, `README.md` with API docs (endpoint table + curl examples), Mermaid ER
diagram, demo script, `.env.example`, `requirements.txt`. Final report to the user listing
work done per SRS requirement and usage instructions.

## 11. Out of scope

Automated tests, JWT, ORM, vector DB, password reset, email, roles beyond owner-check,
deployment, pagination (dataset is demo-sized), React/frameworks (prohibited by SRS).
