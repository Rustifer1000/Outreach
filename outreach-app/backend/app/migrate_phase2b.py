"""One-off migration for Phase 2B: relationship_stage column + notes and contact_connections tables."""
import sys
from pathlib import Path

# Ensure backend is on path when run as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text
from app.database import engine
from app.models import Base, Note, ContactConnection  # noqa: F401 - register models


def run():
    # Add relationship_stage to contacts if not present (SQLite has no IF NOT EXISTS for ADD COLUMN)
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE contacts ADD COLUMN relationship_stage VARCHAR(50)"))
    except Exception as e:
        err = str(e).lower()
        if "duplicate column" in err or "already exists" in err or "no such table" in err:
            pass
        else:
            raise
    # Add in_mention_rotation for daily rotation feature
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE contacts ADD COLUMN in_mention_rotation INTEGER DEFAULT 0"))
    except Exception as e:
        err = str(e).lower()
        if "duplicate column" in err or "already exists" in err or "no such table" in err:
            pass
        else:
            raise
    # Create new tables if they don't exist
    Base.metadata.tables["notes"].create(engine, checkfirst=True)
    Base.metadata.tables["contact_connections"].create(engine, checkfirst=True)
    print("Phase 2B migration done.")


if __name__ == "__main__":
    run()
