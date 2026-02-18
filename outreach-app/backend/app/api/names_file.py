"""API for reading/adding/deleting entries in the Names file."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.names_file import (
    get_names_file_path,
    parse_entries,
    get_categories,
    delete_entry as do_delete_entry,
    add_entry as do_add_entry,
)

router = APIRouter()


@router.get("/entries")
async def list_entries():
    """
    List all contact entries parsed from the Names file.
    Returns name, list_number, role_org, connection_to_solomon, category, subcategory
    (no line numbers exposed).
    """
    path = get_names_file_path()
    if not path.exists():
        return {"entries": [], "path": str(path), "message": "Names file not found"}
    entries = parse_entries(path)
    out = []
    for e in entries:
        out.append({
            "name": e["name"],
            "list_number": e["list_number"],
            "role_org": e["role_org"],
            "connection_to_solomon": e["connection_to_solomon"],
            "category": e["category"],
            "subcategory": e["subcategory"],
        })
    return {"entries": out, "path": str(path)}


@router.get("/categories")
async def list_categories():
    """List category headers as they appear in the Names file (for add-entry dropdown)."""
    path = get_names_file_path()
    categories = get_categories(path)
    return {"categories": categories}


class AddEntryBody(BaseModel):
    category: str
    name: str
    role_org: str = ""
    connection: str
    subcategory: str | None = None
    list_number: int | None = None


@router.post("/entries")
async def add_entry(body: AddEntryBody):
    """Add a new name/entry to the Names file under the given category."""
    path = get_names_file_path()
    try:
        ok = do_add_entry(
            path=path,
            category=body.category,
            name=body.name.strip(),
            role_org=(body.role_org or "").strip(),
            connection=(body.connection or "").strip(),
            subcategory=body.subcategory.strip() if body.subcategory else None,
            list_number=body.list_number,
        )
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Cannot write Names file: {e}")
    if not ok:
        raise HTTPException(status_code=500, detail="Add entry failed")
    return {"ok": True, "message": f"Added {body.name} to {body.category}"}


@router.delete("/entries")
async def delete_entry(
    name: str = Query(..., description="Full name of the entry to remove"),
    list_number: int | None = Query(None, description="Optional list number to disambiguate"),
):
    """
    Remove one entry from the Names file by name.
    If multiple entries share the same name, use list_number to disambiguate.
    """
    path = get_names_file_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Names file not found")
    removed = do_delete_entry(name=name.strip(), list_number=list_number, path=path)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Entry not found: {name}" + (f" (list_number={list_number})" if list_number is not None else ""),
        )
    return {"ok": True, "message": f"Removed {name} from Names file"}
