#!/usr/bin/env python3
"""
Add sample mentions for UI demo (no API keys required).

Usage:
    python seed_sample_mentions.py [--db path]
"""
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Mention, Contact


SAMPLE_MENTIONS = [
    {
        "name_fragment": "Russell",  # Stuart Russell
        "source_type": "news",
        "source_url": "https://example.com/ai-safety-berkeley",
        "title": "UC Berkeley Researchers Call for AI Safety Standards",
        "snippet": "Stuart Russell, professor of computer science, argued that AI systems must be redesigned to be provably beneficial to humans.",
    },
    {
        "name_fragment": "Tegmark",
        "source_type": "news",
        "source_url": "https://example.com/fli-ai-risk",
        "title": "Future of Life Institute Hosts Global AI Risk Summit",
        "snippet": "Max Tegmark's organization convened researchers to discuss existential AI risk and institutional protection.",
    },
    {
        "name_fragment": "Bengio",
        "source_type": "news",
        "source_url": "https://example.com/bengio-regulation",
        "title": "Turing Award Winner Advocates for AI Regulation",
        "snippet": "Yoshua Bengio has pivoted toward AI safety and public advocacy for regulation.",
    },
    {
        "name_fragment": "Christiano",
        "source_type": "news",
        "source_url": "https://example.com/arc-alignment",
        "title": "Alignment Research Center Develops New Approaches",
        "snippet": "Paul Christiano's work on ensuring AI systems follow human intent continues to influence the field.",
    },
    {
        "name_fragment": "Karnofsky",
        "source_type": "news",
        "source_url": "https://example.com/open-phil-ai",
        "title": "Open Philanthropy Directs Millions to AI Safety",
        "snippet": "Holden Karnofsky's 'most important century' thesis frames funding priorities.",
    },
    {
        "name_fragment": "Diamandis",
        "source_type": "news",
        "source_url": "https://example.com/xprize-moonshots",
        "title": "XPRIZE Founder on Technology Optimism",
        "snippet": "Peter Diamandis discusses moonshots and AI's potential at Singularity University event.",
    },
    {
        "name_fragment": "Harris",
        "source_type": "news",
        "source_url": "https://example.com/social-dilemma-ai",
        "title": "Center for Humane Technology Warns of AI Harms",
        "snippet": "Tristan Harris extends his technology critique to AI and institutional disruption.",
    },
    {
        "name_fragment": "Gebru",
        "source_type": "news",
        "source_url": "https://example.com/dair-ai-harms",
        "title": "Distributed AI Research Institute Studies Algorithmic Bias",
        "snippet": "Timnit Gebru leads research on AI harms to marginalized communities.",
    },
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=str, default="sqlite:///./backend/outreach.db")
    args = parser.parse_args()

    db_url = args.db
    if not db_url.startswith("sqlite"):
        print("Use default SQLite path for this script")
        db_url = "sqlite:///./backend/outreach.db"

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)

    session = Session()
    try:
        # Get contacts by name fragment
        contacts = {c.name: c for c in session.query(Contact).all()}

        added = 0
        base_date = datetime.utcnow() - timedelta(days=3)

        for i, sample in enumerate(SAMPLE_MENTIONS):
            # Find matching contact
            contact = next(
                (c for name, c in contacts.items() if sample["name_fragment"] in name),
                None,
            )
            if not contact:
                continue

            # Check if we already have this mention (by URL)
            existing = (
                session.query(Mention)
                .filter(
                    Mention.contact_id == contact.id,
                    Mention.source_url == sample["source_url"],
                )
                .first()
            )
            if existing:
                continue

            mention = Mention(
                contact_id=contact.id,
                source_type=sample["source_type"],
                source_url=sample["source_url"],
                title=sample["title"],
                snippet=sample["snippet"],
                published_at=base_date + timedelta(hours=i * 4),
            )
            session.add(mention)
            added += 1

        session.commit()
        print(f"Added {added} sample mentions. Refresh the dashboard to see them.")
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    exit(main())
