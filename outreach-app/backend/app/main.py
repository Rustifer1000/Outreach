"""
Solomon Outreach API - FastAPI application entry point.
"""
import logging
from sqlalchemy import inspect, text
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, contacts, digest, enrichment, mentions, network, notes, outreach, settings_api, templates
from app.database import engine
from app.models import Base

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

# Add any missing columns to existing tables (lightweight auto-migration)
inspector = inspect(engine)
for table_name, table in Base.metadata.tables.items():
    if table_name in inspector.get_table_names():
        existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
        for column in table.columns:
            if column.name not in existing_cols:
                col_type = column.type.compile(engine.dialect)
                with engine.begin() as conn:
                    conn.execute(text(
                        f'ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}'
                    ))
                logger.info(f"Added missing column {table_name}.{column.name}")

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
