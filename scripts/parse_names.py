#!/usr/bin/env python3
"""
Parse the Solomon Influencer Flywheel Names file into structured JSON/CSV records.

Extracts: name, category, connection_to_solomon, org/role, list_number

Usage:
    python parse_names.py [--output json|csv|both] [--input path/to/Names]
"""

import argparse
import json
import re
import csv
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Contact:
    """Structured contact record from Names file."""
    list_number: Optional[int]
    name: str
    role_org: str
    connection_to_solomon: str
    category: str
    subcategory: Optional[str] = None


def parse_names_file(input_path: Path) -> list[Contact]:
    """Parse the Names file and return a list of Contact records."""
    text = input_path.read_text(encoding="utf-8")
    contacts: list[Contact] = []
    current_category = ""
    current_subcategory: Optional[str] = None

    # Split into sections by category headers
    # Match: ## Category N: Name (range) or ### Subcategory Name
    category_pattern = re.compile(
        r'^##\s+(.+?)(?:\s+\(\d+[–-]\d+\))?\s*$|^###\s+(.+?)\s*$',
        re.MULTILINE
    )

    # Match contact entries: **N. Name** — Role or **Name** — Role or **N. Name** (no role)
    # Also handles: **N. Name — Subname** — Role and **N. Name (parenthetical)**
    entry_pattern = re.compile(
        r'\*\*\s*(\d+)?\.?\s*(.+?)\s*\*\*\s*'
        r'(?:—\s*(.+?))?(?:\s*\(([^)]+)\))?\s*$',
        re.MULTILINE
    )

    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for category header (## Category X: Name)
        cat_match = re.match(r'^##\s+(.+?)(?:\s+\(\d+[–-]\d+\))?\s*$', line)
        if cat_match:
            current_category = cat_match.group(1).strip()
            current_subcategory = None
            i += 1
            continue

        # Check for subcategory header (### Name)
        subcat_match = re.match(r'^###\s+(.+?)\s*$', line)
        if subcat_match:
            current_subcategory = subcat_match.group(1).strip()
            i += 1
            continue

        # Skip summary table and other non-entry content
        if line.strip().startswith("|") or line.strip() == "---":
            i += 1
            continue

        # Match contact entry: **N. Name** — Role
        entry_match = re.match(r'^\*\*\s*(\d+)?\.?\s*(.+?)\s*\*\*\s*(.*)$', line)
        if entry_match:
            num_str, name_part, rest = entry_match.groups()
            list_number = int(num_str) if num_str else None
            name = name_part.strip()

            # Parse role/org from rest - could be "— Role" or "(posthumous...)" or empty
            role_org = ""
            if rest.strip().startswith("—"):
                role_org = rest.strip().lstrip("—").strip()
            elif rest.strip().startswith("("):
                # e.g. (posthumous — ...) - use as role for context
                role_org = rest.strip()
            else:
                role_org = rest.strip() if rest.strip() else ""

            # Next line(s) should be "Connection: ..."
            connection = ""
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if next_line.strip().startswith("Connection:"):
                    connection = next_line.replace("Connection:", "").strip()
                    # Connection might continue on following lines until we hit blank or next **
                    j += 1
                    while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith("**"):
                        connection += " " + lines[j].strip()
                        j += 1
                    break
                elif next_line.strip() == "" or next_line.strip().startswith("**"):
                    break
                j += 1

            # Skip cross-listed, duplicate, or reference-only entries
            if "(duplicate, replacing with:" in connection or "(duplicate, replacing with:" in role_org:
                i = j if j > i else i + 1
                continue

            # Use category from parent if in subcategory section
            effective_category = current_subcategory or current_category
            if not effective_category:
                effective_category = "Uncategorized"

            # Skip header/false entries (Purpose:, Strategy:, etc.)
            if name in ("Purpose:", "Strategy:") or (not connection and not list_number and effective_category == "Uncategorized"):
                i = j if j > i else i + 1
                continue

            contact = Contact(
                list_number=list_number,
                name=name.strip(),
                role_org=role_org,
                connection_to_solomon=connection,
                category=effective_category,
                subcategory=current_subcategory,
            )
            contacts.append(contact)
            i = j if j > i else i + 1
            continue

        i += 1

    return contacts


def main():
    parser = argparse.ArgumentParser(description="Parse Solomon Names file into structured data")
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=Path(__file__).parent.parent / "Names",
        help="Path to Names file",
    )
    parser.add_argument(
        "--output", "-o",
        choices=["json", "csv", "both"],
        default="both",
        help="Output format",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data",
        help="Output directory for generated files",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)

    contacts = parse_names_file(args.input)
    print(f"Parsed {len(contacts)} contacts from {args.input}")

    # Convert to dict list for output
    records = [asdict(c) for c in contacts]

    if args.output in ("json", "both"):
        json_path = args.out_dir / "contacts.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        print(f"Wrote {json_path}")

    if args.output in ("csv", "both"):
        csv_path = args.out_dir / "contacts.csv"
        if records:
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
        print(f"Wrote {csv_path}")

    return 0


if __name__ == "__main__":
    exit(main())
