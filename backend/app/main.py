"""
MetraCheck FastAPI application.

AI-assisted compliance screening and evidence management for Legal
Metrology inspections -- not an automated legal decision-maker. See
CLAUDE.md and PRD.md for the full product framing.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from .config import settings
from .routers import (
    audit,
    compliance,
    dashboard,
    declarations,
    demo,
    evidence,
    inspections,
    ocr,
    repository,
    reports,
    review,
    rules,
)
from .routers import auth as auth_router
from .services.demo.assets_generator import generate_all_demo_assets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("metracheck")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.STORAGE_ROOT).mkdir(parents=True, exist_ok=True)
    Path(settings.DEMO_ASSETS_ROOT).mkdir(parents=True, exist_ok=True)
    try:
        written = generate_all_demo_assets()
        if written:
            logger.info("Generated %d demo asset image(s) on startup.", len(written))
    except Exception:
        logger.exception("Could not generate demo assets on startup (Load Hackathon Demo may fail).")
    yield


app = FastAPI(
    title="MetraCheck API",
    description=(
        "AI-assisted compliance screening and evidence management for Legal Metrology "
        "inspections. Prototype rule pack — verify against active official legal "
        "instruments before operational enforcement. Automated results are explainable "
        "and reviewable; the final enforcement decision is always attributable to an "
        "officer, never to the model."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.STORAGE_ROOT).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.STORAGE_ROOT), name="media")

app.include_router(auth_router.router)
app.include_router(inspections.router)
app.include_router(evidence.router)
app.include_router(ocr.router)
app.include_router(declarations.router)
app.include_router(compliance.router)
app.include_router(review.router)
app.include_router(reports.router)
app.include_router(repository.router)
app.include_router(rules.router)
app.include_router(audit.router)
app.include_router(dashboard.router)
app.include_router(demo.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/", tags=["meta"])
def root():
    return {
        "app": settings.APP_NAME,
        "docs": "/docs",
        "health": "/health",
        "message": "AI-assisted compliance screening and evidence management for Legal Metrology inspections.",
    }
#end of file