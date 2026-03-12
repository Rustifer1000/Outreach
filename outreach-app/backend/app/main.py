"""
Solomon Outreach API - FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, contacts, digest, enrichment, mentions, network, notes, outreach, settings_api, templates
from app.database import engine
from app.models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
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
app.include_router(notes.router, prefix="/api/notes", tags=["notes"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(network.router, prefix="/api/network", tags=["network"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(enrichment.router, prefix="/api/enrichment", tags=["enrichment"])
app.include_router(digest.router, prefix="/api/digest", tags=["digest"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])


@app.get("/")
async def root():
    """Health check / API info."""
    return {
        "name": "Solomon Outreach API",
        "version": "0.1.0",
        "status": "ok",
        "docs": "/docs",
    }
