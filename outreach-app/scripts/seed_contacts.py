#!/usr/bin/env python3
"""
Seed the database with contacts from the parsed Names file.

Usage:
    python seed_contacts.py [--db path/to/outreach.db]
"""
import argparse
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import after path is set
from app.database import Base
from app.models import Contact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        type=str,
        default="sqlite:///./outreach.db",
        help="Database URL",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path(__file__).parent.parent.parent / "data" / "contacts.json",
        help="Path to contacts.json",
    )
    parser.add_argument("--reset", action="store_true", help="Drop and recreate tables")
    args = parser.parse_args()

    engine = create_engine(args.db, connect_args={"check_same_thread": False} if "sqlite" in args.db else {})
    Session = sessionmaker(bind=engine)

    if args.reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    if not args.data.exists():
        print(f"Error: Data file not found: {args.data}")
        print("Run parse_names.py first to generate contacts.json")
        return 1

    with open(args.data, encoding="utf-8") as f:
        records = json.load(f)

    session = Session()
    try:
        for r in records:
            contact = Contact(
                list_number=r.get("list_number"),
                name=r["name"],
                category=r.get("category"),
                subcategory=r.get("subcategory"),
                role_org=r.get("role_org"),
                connection_to_solomon=r.get("connection_to_solomon"),
            )
            session.add(contact)
        session.commit()
        print(f"Seeded {len(records)} contacts into database")
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    exit(main())
