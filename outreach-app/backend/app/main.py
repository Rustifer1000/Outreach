"""
Solomon Outreach API - FastAPI application entry point.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import contacts, mentions, outreach, jobs, names_file, relationship_map
from app.scheduler import get_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create missing tables, run Phase 2B migration (idempotent), start scheduler on startup, stop on shutdown."""
    try:
        from app.database import Base, engine
        import app.models  # noqa: F401 - register all models
        Base.metadata.create_all(engine)
        from app.migrate_phase2b import run as run_migrate
        run_migrate()
    except Exception:
        pass  # e.g. DB not yet created; seed_contacts --reset will create tables
    scheduler = get_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    lifespan=lifespan,
    title="Solomon Outreach API",
    description="API for the Solomon Influencer Flywheel outreach application",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(mentions.router, prefix="/api/mentions", tags=["mentions"])
app.include_router(outreach.router, prefix="/api/outreach", tags=["outreach"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(names_file.router, prefix="/api/names-file", tags=["names-file"])
app.include_router(relationship_map.router, prefix="/api/relationship-map", tags=["relationship-map"])


@app.get("/")
async def root():
    """Health check / API info."""
    return {
        "name": "Solomon Outreach API",
        "version": "0.1.0",
        "status": "ok",
        "docs": "/docs",
    }
