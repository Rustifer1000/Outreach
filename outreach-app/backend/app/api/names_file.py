"""API for reading/adding/deleting entries in the Names file."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.names_file import (
    get_names_file_path,
    parse_entries,
    get_categories,
    delete_entry as do_delete_entry,
    add_entry as do_add_entry,
    edit_entry as do_edit_entry,
    add_category as do_add_category,
    rename_category as do_rename_category,
    delete_category as do_delete_category,
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


class AddCategoryBody(BaseModel):
    name: str


@router.post("/categories")
async def add_category(body: AddCategoryBody):
    """Add a new category section to the Names file."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required")
    path = get_names_file_path()
    try:
        ok = do_add_category(category=name, path=path)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Cannot write Names file: {e}")
    if not ok:
        raise HTTPException(status_code=409, detail=f"Category already exists: {name}")
    return {"ok": True, "message": f"Added category: {name}"}


class RenameCategoryBody(BaseModel):
    old_name: str
    new_name: str


@router.put("/categories")
async def rename_category(body: RenameCategoryBody):
    """Rename a category in the Names file."""
    old_name = body.old_name.strip()
    new_name = body.new_name.strip()
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="Both old_name and new_name are required")
    path = get_names_file_path()
    try:
        ok = do_rename_category(old_name=old_name, new_name=new_name, path=path)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Cannot write Names file: {e}")
    if not ok:
        raise HTTPException(status_code=404, detail=f"Category not found or new name already exists")
    return {"ok": True, "message": f"Renamed '{old_name}' to '{new_name}'"}


@router.delete("/categories")
async def delete_category_endpoint(
    name: str = Query(..., description="Category name to remove"),
):
    """Remove an empty category from the Names file."""
    path = get_names_file_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Names file not found")
    try:
        result = do_delete_category(category=name.strip(), path=path)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Cannot write Names file: {e}")
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["reason"])
    return {"ok": True, "message": f"Removed category: {name}"}


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


class EditEntryBody(BaseModel):
    original_name: str
    original_list_number: int | None = None
    name: str
    role_org: str = ""
    connection: str
    category: str
    subcategory: str | None = None
    list_number: int | None = None


@router.put("/entries")
async def edit_entry(body: EditEntryBody):
    """Edit an existing entry in the Names file."""
    path = get_names_file_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Names file not found")
    try:
        ok = do_edit_entry(
            path=path,
            original_name=body.original_name.strip(),
            original_list_number=body.original_list_number,
            name=body.name.strip(),
            role_org=(body.role_org or "").strip(),
            connection=(body.connection or "").strip(),
            category=body.category.strip(),
            subcategory=body.subcategory.strip() if body.subcategory else None,
            list_number=body.list_number,
        )
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Cannot write Names file: {e}")
    if not ok:
        raise HTTPException(status_code=404, detail=f"Entry not found: {body.original_name}")
    return {"ok": True, "message": f"Updated {body.name}"}


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
