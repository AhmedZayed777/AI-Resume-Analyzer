import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .db import init_db
from .routers import advisor, auth, jobs, resumes

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Resume Analyzer",
    version="1.0.0",
    description="Analyze resumes with AI agents, match jobs, and get RAG-grounded career advice.",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(advisor.router)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err["loc"] if x != "body") or "body"
        parts.append(f"{loc}: {err['msg']}")
    return JSONResponse(status_code=422, content={"detail": "; ".join(parts)})


@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.mount("/", StaticFiles(directory=config.BASE_DIR / "static", html=True), name="static")
