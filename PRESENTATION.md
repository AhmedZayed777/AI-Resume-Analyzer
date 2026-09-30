# AI Resume Analyzer — Complete Project Guide (Presentation Companion)

> Everything about this project in plain English: what it is, how every part works,
> what files exist and why, what went wrong during development, and how to run it.
> Use this next to your slides — each section maps to a presentation topic.

---

## 1. What This Project Is

**The problem:** Job seekers send the same resume to many jobs. Recruiters ask: *"Does this person match OUR job?"* Nobody has time to check that manually for every applicant.

**Our solution:** A web app where you:

1. **Upload your resume** (PDF or DOCX)
2. The app **reads it like a recruiter** — pulls out your skills, education, experience, strengths and weaknesses
3. **Scores you against every job** (0–100) and shows exactly which skills you match and which you're missing
4. Gives you a **personalized improvement plan** (what to learn, which certificates, which resources)
5. Lets you **ask a career advisor** any question — like *"What should I learn next for a backend job?"* — and get answers grounded in a curated knowledge base, not random AI guesses

**In one sentence:** *An AI-powered resume analyzer that extracts, matches, improves, and advises.*

---

## 2. Tech Stack — What We Used and Why

| Layer | Technology | Plain-English reason |
|---|---|---|
| Backend | **Python + FastAPI** | The rulebook (SRS) required Python + FastAPI. FastAPI turns Python functions into web endpoints automatically and gives us free API documentation. |
| Database | **SQLite** | A database that is just *one file* (`data/app.db`). No server to install. Required by the SRS. |
| Frontend | **Plain HTML + CSS + JavaScript** | No React, no Angular, no frameworks (SRS rule). The browser loads simple files from `static/`. |
| AI | **LangChain + an LLM (Groq)** | LangChain is a Python library that makes talking to AI models easy — structured output, tools, and agent loops. |
| Authentication | **Session cookie + PBKDF2** | Standard secure login: passwords are stored as unreadable hashes; after login the server gives your browser a secret cookie. |

**Where the rules come from:** the SRS document (`AI_Resume_Analyzer.pdf`) fixed the stack: *Python + FastAPI only, SQLite only, vanilla JS only.* Everything else was our design choice.

---

## 3. How It Works — The Big Picture

```
┌─────────────────────────────┐
│   YOUR BROWSER              │   static/ → login.html, index.html,
│   (HTML + vanilla JS)       │           analyze.html, jobs.html, advisor.html
└──────────────┬──────────────┘
               │  fetch() calls like POST /api/resumes  (with login cookie)
               ▼
┌─────────────────────────────┐
│   FASTAPI BACKEND           │   app/main.py assembles everything
│   app/routers/              │
│   ├── auth.py    (login)    │   1. Validates input (Pydantic)     → 422 if bad
│   ├── resumes.py (upload)   │   2. Checks login cookie            → 401 if missing
│   ├── jobs.py    (CRUD)     │   3. Checks you own the resource    → 403 if not
│   └── advisor.py (chat)     │   4. Does the work → returns JSON
└──────┬───────────────┬──────┘
       │               │
       ▼               ▼
┌────────────┐   ┌─────────────────────────┐
│  SQLITE    │   │  AI AGENTS (LangChain)  │
│  data/     │   │  1. Resume Analyzer     │  ← reads resume text
│  app.db    │   │  2. Job Matcher         │  ← scores you vs jobs
│  7 tables  │   │  3. Career Advisor      │  ← RAG chat + advice
└────────────┘   └────────────┬────────────┘
                              │  HTTPS (OpenAI-compatible API)
                              ▼
                     ┌─────────────────┐
                     │  LLM PROVIDER   │  Groq (free-tier)
                     │  gpt-oss-120b   │  (was OpenRouter before)
                     └─────────────────┘
```

### The user's journey (5 screens)

1. **`login.html` / `register.html`** — create an account or use the demo user
2. **`index.html`** — dashboard, lists your recent resumes
3. **`analyze.html`** — drag & drop your resume → see skill chips, summary, strengths/weaknesses, **5 job matches with score bars**, and a "Get plan" box for improvement suggestions
4. **`jobs.html`** — search jobs (keyword/location/skill), add/edit/delete your own job postings
5. **`advisor.html`** — chat with the AI career advisor, optionally with your resume attached as context

---

## 4. File Structure — Every Folder and File Explained

```
Project Resume Analyzer/
│
├── app/                        ← ALL the backend Python code
│   ├── __init__.py             ← marks the folder as a Python package
│   ├── main.py                 ← THE APP: creates FastAPI, loads routers,
│   │                               serves the frontend, error handlers
│   ├── config.py               ← reads .env (API key, limits) so settings live in one place
│   ├── db.py                   ← database connection + creates/seeds the DB on first run
│   ├── schema.sql              ← the 7-table blueprint (CREATE TABLE statements)
│   ├── security.py             ← password hashing (PBKDF2) + login sessions
│   │
│   ├── routers/                ← one file per feature = one set of API endpoints
│   │   ├── auth.py             ← register / login / logout / whoami
│   │   ├── resumes.py          ← upload resume, get analysis, matches, improvement plan
│   │   ├── jobs.py             ← list/search/create/edit/delete jobs
│   │   └── advisor.py          ← ask the career advisor a question
│   │
│   ├── agents/                 ← the AI brains (LangChain)
│   │   ├── resume_analyzer.py  ← Agent 1: resume text → structured data
│   │   ├── job_matcher.py      ← Agent 2: score resume vs each job
│   │   ├── career_advisor.py   ← Agent 3: RAG chat + improvement plans
│   │   ├── knowledge.py        ← search engine for the knowledge base
│   │   ├── llm.py              ← connects to the AI provider (with retries)
│   │   └── schemas.py          ← the "shapes" of AI output (Pydantic models)
│   │
│   └── services/
│       └── extraction.py       ← reads PDF/DOCX files into plain text
│
├── static/                     ← ALL the frontend (no frameworks)
│   ├── login.html              ← login page
│   ├── register.html           ← sign-up page
│   ├── index.html              ← dashboard / home
│   ├── analyze.html            ← upload + results + matches + improve
│   ├── jobs.html               ← job search + management
│   ├── advisor.html            ← AI chat page
│   ├── css/style.css           ← all styling (dark theme, cards, score bars)
│   └── js/
│       ├── api.js              ← helper: call the backend, show errors as toasts
│       ├── auth.js             ← login/register forms + "Hi, name" in the navbar
│       ├── analyze.js          ← upload logic, render analysis & matches
│       ├── jobs.js             ← search, list, add/edit/delete modal
│       └── advisor.js          ← chat messages + resume-context selector
│
├── data/
│   └── app.db                  ← the SQLite database (auto-created, never edit by hand)
│
├── docs/superpowers/           ← development paperwork
│   ├── specs/...design.md      ← the approved design document
│   └── plans/...analyzer.md    ← the 16-step implementation plan
│
├── .env                        ← SECRETS: your AI API key (git-ignored, never share)
├── .env.example                ← template showing which settings .env needs
├── .gitignore                  ← tells git to ignore .env and the database
├── requirements.txt            ← the Python packages to install (FastAPI, LangChain…)
├── README.md                   ← API documentation + ER diagram + quick start
├── PRESENTATION.md             ← this file
├── demo.py                     ← old command-line demo of the AI agents
├── logconfig.json              ← writes server logs to uvicorn.log
└── uvicorn.log                 ← the server log (errors appear here)
```

**Golden rule:** `app/` = backend brain, `static/` = what you see, `data/` = memory, `.env` = secrets.

---

## 5. The Database — 7 Tables in Plain Words

A database table is like a spreadsheet: rows = records, columns = facts about them.

| Table | What one row means | Key columns |
|---|---|---|
| **users** | one registered person | email, password_hash (never plain text!), full_name |
| **sessions** | one active login on some device | token (the cookie value), user_id, expires_at |
| **jobs** | one job posting | title, company, description, required_skills (JSON list), created_by (who posted it) |
| **resumes** | one uploaded file | user_id, filename, raw_text (the extracted text) |
| **analyses** | what the AI found in that resume | skills, education, experience, summary, strengths, weaknesses (all JSON) |
| **matches** | "resume X fits job Y with score Z" | resume_id, job_id, score, matched_skills, missing_skills, explanation |
| **knowledge** | one article in the advisor's knowledge base | category, title, content (roadmaps, certifications, resume tips…) |

### ER diagram (who connects to whom)

```mermaid
erDiagram
    USERS ||--o{ SESSIONS : "logs in"
    USERS ||--o{ RESUMES : uploads
    USERS ||--o{ JOBS : creates
    RESUMES ||--o| ANALYSES : has
    RESUMES ||--o{ MATCHES : receives
    JOBS ||--o{ MATCHES : participates_in

    USERS      { int id PK, text email UK, text password_hash, text full_name }
    SESSIONS   { text token PK, int user_id FK, text expires_at }
    JOBS       { int id PK, text title, text required_skills, int created_by FK }
    RESUMES    { int id PK, int user_id FK, text filename, text raw_text }
    ANALYSES   { int id PK, int resume_id FK, text summary, text technical_skills }
    MATCHES    { int id PK, int resume_id FK, int job_id FK, real score }
    KNOWLEDGE  { int id PK, text category, text title, text content }
```

Reading it: *"One user uploads many resumes; one resume has exactly one analysis and many matches; a match connects one resume to one job."*

**Auto-seeding:** the first time the app runs it creates the database and fills it with a demo user (`demo@example.com` / `demo12345`), 8 example jobs, and 16 knowledge articles — so the app works immediately.

---

## 6. The FastAPI Part — Explained From Scratch

### What is FastAPI?

FastAPI is a Python library. You write normal Python functions and add "decorators" (the `@router.get(...)` lines) that tell it: *when someone requests this URL, run this function, and send back what it returns as JSON.* It also reads your type hints to validate input and document the API automatically.

### The pieces we use

**1. The app — `app/main.py`**
```python
app = FastAPI(lifespan=lifespan)        # lifespan = start-up hook → creates the database
app.include_router(auth.router)         # attach each feature's endpoints
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(advisor.router)
app.mount("/", StaticFiles(directory="static", html=True))  # serve the HTML pages
```
Also here: **error handlers** so users never see a raw Python crash:
- wrong input → friendly `422 {"detail": "password: must be at least 6 characters"}`
- any unexpected bug → `500 {"detail": "Internal server error"}` (full traceback goes to `uvicorn.log` instead)

**2. Routers — one file per feature**
```python
router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("")                              # GET /api/jobs
def list_jobs(q: str | None = None, ...):    # ?q=backend is read from the URL
    return [ ...list of jobs as JSON... ]
```

**3. Pydantic models — input validation for free**
```python
class RegisterIn(BaseModel):
    email: str = Field(min_length=5)
    password: str = Field(min_length=6)      # a 3-char password never reaches our code
```
Bad input is rejected instantly with **422** — FastAPI does it automatically.

**4. Dependencies (`Depends`) — the login guard**
```python
def get_current_user(sid: str = Cookie(default=None)):
    # look up cookie 'sid' in the sessions table → return the user
    # not found/expired → raise 401 "Not logged in"

@router.get("/me")
def me(user: dict = Depends(get_current_user)):   # <- logged-in users only
    return user
```
One line protects any endpoint. Same pattern for ownership: editing someone else's job → **403**, touching a resume that isn't yours → **404** (pretend it doesn't exist).

**5. Status codes we return**

| Code | Meaning | Example |
|---|---|---|
| 200 | OK | normal requests |
| 201 | Created | new account, new job, resume analyzed |
| 401 | Not logged in | cookie missing/expired |
| 403 | Forbidden | editing another user's job |
| 404 | Not found | wrong ID or someone else's resume |
| 409 | Conflict | registering an email that already exists |
| 422 | Bad input | password too short, invalid JSON |
| 500 | Our bug | unexpected error (details logged, not shown) |
| 502 | AI provider problem | LLM down/rate-limited — message explains why |

**6. Free documentation** — start the server and open **http://127.0.0.1:8000/docs**: every endpoint with its parameters, and a "Try it out" button. Generated automatically from the code.

### Walkthrough of one real request

```
You drop resume.pdf on analyze.html
  → JS sends:  POST /api/resumes  (multipart file + your login cookie)
  → FastAPI:   Depends(get_current_user)     → finds your session → OK
  → size check (≤ 5 MB)                      → else 400
  → services/extraction.py reads the PDF     → else 400 "unreadable"
  → INSERT the resume row into SQLite
  → agents/resume_analyzer.py sends text to the LLM with a strict output
    schema (tool calling)                    → else 502 (with a clear reason)
  → save analysis → agents/job_matcher.py scores all 8 jobs
  → 201 {"resume_id": 10, "analysis": {...}}
  → browser renders: skill chips, score bars, explanations
```

---

## 7. The 3 AI Agents + RAG — Explained Simply

All three live in `app/agents/` and use **LangChain**, a library that standardizes how Python talks to AI models.

### What LangChain adds (in 4 bullets)
- **Chat models:** one line to connect to any OpenAI-compatible provider (Groq, OpenRouter, OpenAI, Ollama at home…)
- **Structured output:** you give the AI a "shape" (our `ResumeAnalysis` schema) and it MUST fill it — no free-form prose we'd have to parse
- **Tools:** the AI can *call functions* you wrote (like a search button)
- **Agents:** a loop — model thinks → calls a tool → sees the result → answers

### Agent 1 — Resume Analyzer (`resume_analyzer.py`)
- **Job in:** raw resume text (up to 12,000 characters)
- **Job out:** a filled `ResumeAnalysis` object: name, email, technical skills, soft skills, education, experience, years, summary, strengths, weaknesses
- **How:** one LLM call with the system prompt *"You are an expert technical recruiter… never invent skills or dates"* + strict schema
- **Result in the UI:** the profile cards and skill chips on `analyze.html`

### Agent 2 — Job Matcher (`job_matcher.py`)
- **The score is a formula, not an AI guess** (so it's consistent and explainable):
  ```
  score = 100 × (0.75 × skills you have ÷ skills required  +  0.25 × experience fit)
  ```
  Example: job needs Python, FastAPI, Docker; you have 2 of 3 → 100 × (0.75×⅔ + 0.25×1) = **75/100**
- **The explanation is AI:** for each top match, the LLM writes 1–2 sentences: *"Matched Python and FastAPI; missing Docker…"*
- **Fallback:** if the AI is down, a rule-based sentence is generated instead — scoring never breaks

### Agent 3 — Career Advisor (`career_advisor.py`) — this is where **RAG** happens

**RAG = Retrieval-Augmented Generation:** *search first, then answer.*
Plain AI answers come from training data — it might invent fake course names. RAG feeds the model real documents from our `knowledge` table right before it answers.

```
You ask: "What should I learn next for a backend job?"
   ↓
Tool: search_knowledge_base("backend developer roadmap")
   ↓
knowledge.py compares words & returns the 4 best articles
   (backend roadmap, Python skills, Docker, resume guidelines)
   ↓
The model MUST answer using those articles
   ↓
Answer cites the roadmap — no invented certifications
```

The system prompt enforces it: *"Always call search_knowledge_base before recommending courses or roadmaps."* You can see this working — real answer from our tests: *"All suggestions are drawn directly from the roadmap; no external course names are invented."*

The same retrieval feeds the **improvement plan** (missing skills, improvements, certifications, resources).

### Retry & error handling (the LLM can be moody)
- Every AI call has **retries with backoff** (`call_with_retry` in `llm.py`) — survives the provider's temporary 429/503 errors
- If it still fails, the endpoint returns **502** with a precise message — e.g. *"free daily quota exhausted… resets at 00:00 UTC"* — never a silent crash

---

## 8. Security — How We Protect Users

| Threat | Our defense |
|---|---|
| Someone steals the database | Passwords saved as **PBKDF2-SHA256** (200,000 rounds + unique salt) — not readable, not reversible |
| Stolen/forged login | Login creates a random 64-char **session token** stored in an HttpOnly cookie (`sid`); the raw password is never re-sent |
| Session theft via scripts | Cookie is **HttpOnly** (JavaScript can't read it) + **SameSite=Lax** (other sites can't ride it) |
| User A edits User B's job | **Ownership checks** → 403; resumes of others → 404 |
| Oversized/malicious files | 5 MB limit, PDF/DOCX extension allow-list, text-extraction guard |
| Secrets in the repo | `.env` is in `.gitignore` — the key never gets committed |
| Attack payloads in output | Frontend escapes everything rendered (`escapeHtml`) — no XSS |
| API abuse | Pydantic `Field` limits on every string (length caps) |

---

## 9. API Reference (all 16 endpoints)

Base URL: `http://127.0.0.1:8000` — everything is JSON. Auth = `sid` cookie.
Interactive version: **/docs**

| Method | Path | Body / params | Returns |
|---|---|---|---|
| POST | `/api/auth/register` | `{email, password, full_name?}` | 201 user + cookie |
| POST | `/api/auth/login` | `{email, password}` | user + cookie |
| POST | `/api/auth/logout` | — | `{ok}` |
| GET | `/api/auth/me` | — | current user or 401 |
| POST | `/api/resumes` | multipart `file` | 201 `{resume_id, analysis}` |
| GET | `/api/resumes` | — | your resumes |
| GET | `/api/resumes/{id}` | — | one resume + analysis |
| GET | `/api/resumes/{id}/matches` | — | up to 5 scored jobs |
| POST | `/api/resumes/{id}/improve` | `{target_role}` | improvement plan |
| GET | `/api/jobs` | `?q=&location=&skill=` | filtered jobs |
| POST | `/api/jobs` | `{title, company?, location?, description?, required_skills?, min_years_experience?}` | 201 job (yours) |
| GET | `/api/jobs/{id}` | — | one job |
| PUT | `/api/jobs/{id}` | same as POST | updated job — owner only (403 otherwise) |
| DELETE | `/api/jobs/{id}` | — | `{ok}` — owner only |
| POST | `/api/advisor/ask` | `{question, resume_id?, history?}` | `{answer}` |

---

## 10. The Development Story (great material for "challenges" slides)

The project was built from a written design spec → a 16-step plan → step-by-step with verification after every step. Real problems we hit and fixed:

1. **Broken package:** the AI folder had `init.py` instead of `__init__.py` → Python couldn't import it. *Renamed it.*
2. **Disappearing AI model:** the SRS-suggested free model was made paid by the provider → all calls failed with 404. *Queried the provider's model list live and switched to a free tool-capable model.*
3. **Truncated AI output:** the model's JSON was cut off mid-way (default output cap too small). *Set `max_tokens=4096`.*
4. **Mysterious 500 on upload:** we called `json.dumps()` on Python objects that weren't JSON-ready (pydantic models). The resume was saved but the analysis wasn't. *Added `.model_dump()` — classic serialization bug.*
5. **Invisible errors:** the 502 handler swallowed the real exception — no way to debug. *Added server-side logging (`logger.exception`) + log file.*
6. **Flaky free AI:** the free provider threw 429 (rate limit) and 503 (overloaded) bursts. *Added retries with backoff; never retry a spent daily quota.*
7. **The misleading error:** users saw *"check your API key"* when the real cause was the **50-requests-per-day free quota** being exhausted. *Wrote `describe_ai_error()` so the message tells the truth (quota vs rate-limit vs config).*
8. **Provider switch:** after the quota died mid-testing, we moved from OpenRouter to **Groq** (`openai/gpt-oss-120b`) — requests went from ~40–60 s to **~5 s**.
9. **No browser test = false confidence:** we built a headless-browser walkthrough (Playwright + Edge) that clicks through all 10 acceptance scenarios — **21/22 passed**; the 1 failure was the quota dying live, which then proved the error UI works (red bubble, no crash).

**Numbers to quote:** 16 plan tasks · 7 DB tables · 16 API endpoints · 6 pages · 3 AI agents · 21/22 automated UI checks · ~5 s per AI call.

---

## 11. Run It, Verify It, Close It

### Start
```powershell
cd "D:\work\ITI AI\Project Resume Analyzer"
python -m pip install -r requirements.txt     # first time only
python -m uvicorn app.main:app --reload        # DB creates + seeds itself
```
Open **http://127.0.0.1:8000/** — log in with `demo@example.com` / `demo12345`.

### Verify in 30 seconds
- http://127.0.0.1:8000/docs → Swagger UI loads (200)
- Log in → navbar shows *Hi, Demo User*
- Analyze page → upload `C:\Users\asus\AppData\Local\Temp\sample_resume.docx` → chips + score bars appear

### Close
- If running in a visible terminal: **Ctrl+C**
- If running hidden (as it is now): 
```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

### Housekeeping commands
```powershell
# want a factory-fresh database?  stop the server, then:
Remove-Item -Recurse -Force data      # next start re-seeds demo data

# AI not working?  check the log first:
Get-Content uvicorn.log -Tail 30
```

### Settings (`.env`)
```
LLM_API_KEY=...        # your provider key (Groq active now; OpenRouter lines kept as comments)
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b    # must support tool/function calling
```

---

## 12. Known Limitations (be honest in Q&A)

- **AI needs a working key + quota.** Free tiers run out (OpenRouter: 50/day; Groq: generous but finite). The app degrades gracefully: clear message, everything else still works.
- **The model must support "tool calling"** — structured output and the RAG agent depend on it.
- **Scanned/image-only PDFs are rejected** — we extract text, not images (no OCR).
- **Keyword-based retrieval** — the knowledge search compares words, not meaning (a real vector database would be the upgrade).
- **No automated test suite** — by decision; verification was curl suites + an automated browser walkthrough instead.
- **SQLite = single machine** — perfect for a project, not for thousands of concurrent users.

---

## 13. Glossary (for Q&A)

| Term | Meaning |
|---|---|
| **API** | A URL the program offers. Other software (our frontend) calls it and gets JSON back. |
| **Endpoint** | One API URL + one action (e.g. `POST /api/jobs` = "create a job"). |
| **JSON** | The universal data format for web APIs: `{"name": "Sara", "skills": ["Python"]}`. |
| **Status code** | 3-digit reply number: 2xx good, 4xx your mistake, 5xx our/server's problem. |
| **Router** | FastAPI's way of grouping endpoints by feature (one file = one router). |
| **Pydantic** | Python library that defines data shapes and validates input automatically. |
| **Session cookie** | A secret token in your browser that proves "you are logged in" without sending your password again. |
| **PBKDF2** | A slow, salted password-hashing function — makes stolen hashes expensive to crack. |
| **LLM** | Large Language Model — the AI (ChatGPT-style) that reads and writes text. |
| **Token** | A word-fragment the LLM processes; also = max output length budget. |
| **Tool calling / function calling** | The LLM's ability to invoke code you wrote (e.g. our knowledge search) instead of only generating text. |
| **Structured output** | Forcing the LLM to answer in an exact schema we can parse — no prose. |
| **RAG** | Retrieval-Augmented Generation: search our documents first, answer from them second. |
| **Knowledge base** | Our `knowledge` table: roadmaps, certifications, resume tips the advisor searches. |
| **LangChain** | Python library that standardizes LLM calls, tools, and agent loops. |
| **Agent** | An LLM in a loop: think → call a tool → read result → continue. |
| **Dependency (`Depends`)** | FastAPI's injection trick — run this check (like "must be logged in") before the endpoint. |
| **Migration/seed** | Creating the database schema / filling it with starter data. |

---

*End of companion. Slides → section numbers above. Good luck with the presentation!*
