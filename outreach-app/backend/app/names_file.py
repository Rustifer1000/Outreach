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


def add_category(category: str, path: Optional[Path] = None) -> bool:
    """
    Add a new ## category section at the end of the Names file.
    Returns False if the category already exists.
    """
    path = path or get_names_file_path()
    category = _sanitize_line(category)
    if not category:
        return False

    existing = get_categories(path)
    if category in existing:
        return False

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Solomon Influencer Flywheel List\n\n"
            "---\n\n"
            f"## {category}\n",
            encoding="utf-8",
        )
        return True

    text = path.read_text(encoding="utf-8")
    new_block = f"\n\n---\n\n## {category}\n"
    path.write_text(text.rstrip() + new_block, encoding="utf-8")
    return True


def rename_category(old_name: str, new_name: str, path: Optional[Path] = None) -> bool:
    """
    Rename a ## category header in the Names file.
    Returns False if old_name not found or new_name already exists.
    """
    path = path or get_names_file_path()
    old_name = _sanitize_line(old_name)
    new_name = _sanitize_line(new_name)
    if not old_name or not new_name or old_name == new_name:
        return False
    if not path.exists():
        return False

    existing = get_categories(path)
    if old_name not in existing:
        return False
    if new_name in existing:
        return False

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    cat_pattern = re.compile(r"^##\s+(.+?)(?:\s+\(\d+[–-]\d+\))?\s*$")
    found = False
    for idx, line in enumerate(lines):
        m = cat_pattern.match(line)
        if m and m.group(1).strip() == old_name:
            # Preserve any trailing range notation like (1-10)
            suffix = line[m.end(1):]  # everything after the category name
            lines[idx] = f"## {new_name}{suffix}"
            found = True
            break

    if not found:
        return False

    path.write_text("\n".join(lines) + ("\n" if lines and not lines[-1].endswith("\n") else ""), encoding="utf-8")
    return True


def delete_category(category: str, path: Optional[Path] = None) -> dict:
    """
    Remove a ## category section from the Names file.
    Only succeeds if the category has no entries.
    Returns {"ok": True} on success, or {"ok": False, "reason": "..."} on failure.
    """
    path = path or get_names_file_path()
    category = _sanitize_line(category)
    if not path.exists():
        return {"ok": False, "reason": "Names file not found"}

    # Check if any entries belong to this category
    entries = parse_entries(path)
    entries_in_cat = [e for e in entries if e["category"] == category]
    if entries_in_cat:
        return {"ok": False, "reason": f"Category still has {len(entries_in_cat)} entries. Move or remove them first."}

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    cat_pattern = re.compile(r"^##\s+(.+?)(?:\s+\(\d+[–-]\d+\))?\s*$")

    # Find the category header line
    cat_line = None
    for idx, line in enumerate(lines):
        m = cat_pattern.match(line)
        if m and m.group(1).strip() == category:
            cat_line = idx
            break

    if cat_line is None:
        return {"ok": False, "reason": f"Category not found: {category}"}

    # Remove from cat_line up to (but not including) the next ## header or end of file
    end_line = cat_line + 1
    while end_line < len(lines):
        if lines[end_line].strip().startswith("## "):
            break
        end_line += 1

    # Also remove any preceding separator (---) and blank lines
    start_line = cat_line
    while start_line > 0 and lines[start_line - 1].strip() in ("", "---"):
        start_line -= 1

    new_lines = lines[:start_line] + lines[end_line:]
    path.write_text("\n".join(new_lines) + ("\n" if new_lines and not new_lines[-1].endswith("\n") else ""), encoding="utf-8")
    return {"ok": True}


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


def edit_entry(
    original_name: str,
    name: str,
    role_org: str,
    connection: str,
    category: str,
    subcategory: Optional[str] = None,
    list_number: Optional[int] = None,
    original_list_number: Optional[int] = None,
    path: Optional[Path] = None,
) -> bool:
    """
    Edit an existing entry in the Names file.
    Finds the entry by original_name (and optional original_list_number),
    then replaces its lines with the updated content.
    Returns True if the entry was found and updated.
    """
    path = path or get_names_file_path()
    if not path.exists():
        return False

    name = _sanitize_line(name)
    role_org = _sanitize_line(role_org)
    connection = _sanitize_line(connection)

    entries = parse_entries(path)
    target = None
    for e in entries:
        if e["name"] != original_name:
            continue
        if original_list_number is not None and e["list_number"] != original_list_number:
            continue
        target = e
        break

    if not target:
        return False

    lines = path.read_text(encoding="utf-8").split("\n")
    start, end = target["line_start"], target["line_end"]

    # Build replacement lines (same format as add_entry)
    new_entry_lines = [
        _format_entry_line(list_number, name, role_org),
        "Connection: " + connection,
    ]

    new_lines = lines[:start] + new_entry_lines + lines[end:]
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
