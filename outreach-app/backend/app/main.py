"""
Solomon Outreach API - FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import contacts, mentions, outreach

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


@app.get("/")
async def root():
    """Health check / API info."""
    return {
        "name": "Solomon Outreach API",
        "version": "0.1.0",
        "status": "ok",
        "docs": "/docs",
    }
