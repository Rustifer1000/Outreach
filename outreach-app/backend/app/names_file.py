"""
Read/write the Solomon Names file: parse entries, add entry, delete entry.
Path to Names file: NAMES_FILE_PATH env var, or project root / "Names".
"""
import os
import re
from pathlib import Path
from typing import Optional

# Default: project root is parent of outreach-app (parent of backend)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_NAMES_PATH = _PROJECT_ROOT / "Names"


def get_names_file_path() -> Path:
    path = os.environ.get("NAMES_FILE_PATH")
    if path:
        return Path(path).resolve()
    return DEFAULT_NAMES_PATH


def _sanitize_line(s: str) -> str:
    """Replace newlines with space so one entry stays on one block in the file."""
    return " ".join((s or "").splitlines()).strip()


def _format_entry_line(list_number: Optional[int], name: str, role_org: str) -> str:
    if list_number is not None:
        return f"**{list_number}. {name}** — {role_org}"
    return f"**{name}** — {role_org}"


def parse_entries(path: Optional[Path] = None) -> list[dict]:
    """
    Parse the Names file and return list of entry dicts with:
    name, list_number, role_org, connection_to_solomon, category, subcategory, line_start, line_end.
    """
    path = path or get_names_file_path()
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    entries: list[dict] = []
    current_category = ""
    current_subcategory: Optional[str] = None
    i = 0

    while i < len(lines):
        line = lines[i]

        cat_match = re.match(r"^##\s+(.+?)(?:\s+\(\d+[–-]\d+\))?\s*$", line)
        if cat_match:
            current_category = cat_match.group(1).strip()
            current_subcategory = None
            i += 1
            continue

        subcat_match = re.match(r"^###\s+(.+?)\s*$", line)
        if subcat_match:
            current_subcategory = subcat_match.group(1).strip()
            i += 1
            continue

        if line.strip().startswith("|") or line.strip() == "---":
            i += 1
            continue

        entry_match = re.match(r"^\*\*\s*(\d+)?\.?\s*(.+?)\s*\*\*\s*(.*)$", line)
        if entry_match:
            num_str, name_part, rest = entry_match.groups()
            list_number = int(num_str) if num_str else None
            name = name_part.strip()

            role_org = ""
            if rest.strip().startswith("—"):
                role_org = rest.strip().lstrip("—").strip()
            elif rest.strip().startswith("("):
                role_org = rest.strip()
            else:
                role_org = rest.strip() if rest.strip() else ""

            connection = ""
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if next_line.strip().startswith("Connection:"):
                    connection = next_line.replace("Connection:", "").strip()
                    j += 1
                    while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith("**"):
                        connection += " " + lines[j].strip()
                        j += 1
                    break
                elif next_line.strip() == "" or next_line.strip().startswith("**"):
                    break
                j += 1

            if "(duplicate, replacing with:" in connection or "(duplicate, replacing with:" in role_org:
                i = j if j > i else i + 1
                continue

            effective_category = current_subcategory or current_category or "Uncategorized"
            if name in ("Purpose:", "Strategy:") or (
                not connection and not list_number and effective_category == "Uncategorized"
            ):
                i = j if j > i else i + 1
                continue

            entries.append({
                "name": name,
                "list_number": list_number,
                "role_org": role_org,
                "connection_to_solomon": connection,
                "category": effective_category,
                "subcategory": current_subcategory,
                "line_start": i,
                "line_end": j,
            })
            i = j if j > i else i + 1
            continue

        i += 1

    return entries


def get_categories(path: Optional[Path] = None) -> list[str]:
    """Return list of category headers as they appear in the file (## Category ...)."""
    path = path or get_names_file_path()
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    categories: list[str] = []
    for line in lines:
        cat_match = re.match(r"^##\s+(.+?)(?:\s+\(\d+[–-]\d+\))?\s*$", line)
        if cat_match:
            categories.append(cat_match.group(1).strip())
    return categories


def delete_entry(name: str, list_number: Optional[int] = None, path: Optional[Path] = None) -> bool:
    """
    Remove one entry from the Names file by name (and optional list_number).
    Returns True if an entry was removed, False if not found.
    """
    path = path or get_names_file_path()
    if not path.exists():
        return False

    entries = parse_entries(path)
    target = None
    for e in entries:
        if e["name"] != name:
            continue
        if list_number is not None and e["list_number"] != list_number:
            continue
        target = e
        break

    if not target:
        return False

    lines = path.read_text(encoding="utf-8").split("\n")
    # Remove lines [line_start, line_end); also remove following blank line if present
    start, end = target["line_start"], target["line_end"]
    new_lines = lines[:start] + lines[end:]
    if start < len(new_lines) and new_lines[start].strip() == "":
        new_lines.pop(start)
    path.write_text("\n".join(new_lines) + ("\n" if new_lines and not new_lines[-1].endswith("\n") else ""), encoding="utf-8")
    return True


def add_entry(
    category: str,
    name: str,
    role_org: str,
    connection: str,
    subcategory: Optional[str] = None,
    list_number: Optional[int] = None,
    path: Optional[Path] = None,
) -> bool:
    """
    Append a new entry to the given category in the Names file.
    If category does not exist, appends a new ## category section at the end.
    Returns True on success.
    """
    path = path or get_names_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    name = _sanitize_line(name)
    role_org = _sanitize_line(role_org)
    connection = _sanitize_line(connection)
    category = _sanitize_line(category)
    subcategory = _sanitize_line(subcategory) if subcategory else None

    if not path.exists():
        # Create minimal file with header and one category
        path.write_text(
            "# Solomon Influencer Flywheel List\n\n"
            "---\n\n"
            f"## {category}\n\n"
            f"{_format_entry_line(list_number, name, role_org)}\n"
            f"Connection: {connection}\n",
            encoding="utf-8",
        )
        return True

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Find the category section and the line after the last entry in it
    category_header_pattern = re.compile(r"^##\s+(.+?)(?:\s+\(\d+[–-]\d+\))?\s*$")
    insert_line: Optional[int] = None
    for idx, line in enumerate(lines):
        m = category_header_pattern.match(line)
        if not m or m.group(1).strip() != category:
            continue
        # Found the category; find end of last entry in this section
        insert_line = idx + 1
        k = idx + 1
        while k < len(lines):
            if lines[k].strip().startswith("## "):
                break
            if re.match(r"^\*\*\s*(\d+)?\.?\s*.+\s*\*\*", lines[k]):
                # Start of an entry; skip to after Connection: lines
                insert_line = k + 1
                k += 1
                while k < len(lines) and lines[k].strip() and not lines[k].strip().startswith("**"):
                    insert_line = k + 1
                    k += 1
                continue
            k += 1
        break

    if insert_line is None:
        # Category not found; append new section at end
        new_block = "\n\n---\n\n## " + category + "\n\n"
        new_block += _format_entry_line(list_number, name, role_org) + "\n"
        new_block += "Connection: " + connection + "\n"
        path.write_text(text.rstrip() + new_block, encoding="utf-8")
        return True

    new_entry_lines = [
        "",
        _format_entry_line(list_number, name, role_org),
        "Connection: " + connection,
    ]
    new_lines = lines[:insert_line] + new_entry_lines + lines[insert_line:]
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return True
