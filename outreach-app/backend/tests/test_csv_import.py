"""Tests for POST /api/contacts/import-csv."""
import io
import pytest
from app.models import Contact, ContactInfo


def _csv_file(content: str, filename: str = "contacts.csv"):
    """Helper: package a string as a multipart file upload tuple."""
    return (filename, io.BytesIO(content.encode("utf-8")), "text/csv")


# ---------------------------------------------------------------------------
# Happy-path cases
# ---------------------------------------------------------------------------

def test_import_creates_new_contacts(client, db_session):
    csv = "name,email\nAlice Smith,alice@example.com\nBob Jones,bob@example.com\n"
    r = client.post("/api/contacts/import-csv", files={"file": _csv_file(csv)})
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 2
    assert data["updated"] == 0
    assert data["info_added"] == 2
    assert set(data["created_names"]) == {"Alice Smith", "Bob Jones"}

    contacts = db_session.query(Contact).all()
    assert len(contacts) == 2


def test_import_matches_existing_contact_by_name(client, db_session):
    db_session.add(Contact(name="Alice Smith"))
    db_session.commit()

    csv = "name,email\nAlice Smith,alice@example.com\n"
    r = client.post("/api/contacts/import-csv", files={"file": _csv_file(csv)})
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 0
    assert data["updated"] == 1
    assert data["info_added"] == 1
    assert data["updated_names"] == ["Alice Smith"]

    # Should still only have one contact
    assert db_session.query(Contact).count() == 1


def test_import_case_insensitive_name_match(client, db_session):
    db_session.add(Contact(name="Alice Smith"))
    db_session.commit()

    csv = "name,email\nalice smith,alice@example.com\n"
    r = client.post("/api/contacts/import-csv", files={"file": _csv_file(csv)})
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 0
    assert data["updated"] == 1


def test_import_all_contact_info_types(client, db_session):
    csv = "name,email,linkedin,x,phone,other\nAlice,alice@example.com,linkedin.com/in/alice,@alice,555-1234,alice.com\n"
    r = client.post("/api/contacts/import-csv", files={"file": _csv_file(csv)})
    assert r.status_code == 200
    data = r.json()
    assert data["info_added"] == 5

    contact = db_session.query(Contact).filter_by(name="Alice").first()
    info_types = {ci.type for ci in db_session.query(ContactInfo).filter_by(contact_id=contact.id).all()}
    assert info_types == {"email", "linkedin", "twitter", "phone", "other"}


def test_import_skips_duplicate_contact_info(client, db_session):
    contact = Contact(name="Alice")
    db_session.add(contact)
    db_session.flush()
    db_session.add(ContactInfo(contact_id=contact.id, type="email", value="alice@example.com"))
    db_session.commit()

    csv = "name,email\nAlice,alice@example.com\n"
    r = client.post("/api/contacts/import-csv", files={"file": _csv_file(csv)})
    assert r.status_code == 200
    data = r.json()
    assert data["info_added"] == 0
    assert data["info_skipped_duplicates"] == 1

    # Still only one ContactInfo row
    assert db_session.query(ContactInfo).filter_by(contact_id=contact.id).count() == 1


def test_import_adds_only_new_info_for_existing_contact(client, db_session):
    contact = Contact(name="Alice")
    db_session.add(contact)
    db_session.flush()
    db_session.add(ContactInfo(contact_id=contact.id, type="email", value="alice@example.com"))
    db_session.commit()

    # CSV adds a new LinkedIn URL alongside the existing email
    csv = "name,email,linkedin\nAlice,alice@example.com,linkedin.com/in/alice\n"
    r = client.post("/api/contacts/import-csv", files={"file": _csv_file(csv)})
    assert r.status_code == 200
    data = r.json()
    assert data["info_added"] == 1
    assert data["info_skipped_duplicates"] == 1


def test_import_skips_empty_name_rows(client, db_session):
    csv = "name,email\nAlice,alice@example.com\n,nobody@example.com\nBob,bob@example.com\n"
    r = client.post("/api/contacts/import-csv", files={"file": _csv_file(csv)})
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 2
    assert len(data["skipped_rows"]) == 1
    assert data["skipped_rows"][0]["row"] == 3


def test_import_empty_info_columns_ignored(client, db_session):
    csv = "name,email,linkedin\nAlice,,\n"
    r = client.post("/api/contacts/import-csv", files={"file": _csv_file(csv)})
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 1
    assert data["info_added"] == 0


def test_import_handles_excel_bom(client, db_session):
    """CSV with UTF-8 BOM (common Excel export) should parse correctly."""
    csv_bytes = b"\xef\xbb\xbfname,email\nAlice,alice@example.com\n"
    r = client.post(
        "/api/contacts/import-csv",
        files={"file": ("contacts.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 1
    assert db_session.query(Contact).filter_by(name="Alice").count() == 1


def test_import_mixed_new_and_existing(client, db_session):
    db_session.add(Contact(name="Existing Person"))
    db_session.commit()

    csv = "name,email\nExisting Person,existing@example.com\nNew Person,new@example.com\n"
    r = client.post("/api/contacts/import-csv", files={"file": _csv_file(csv)})
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 1
    assert data["updated"] == 1
    assert data["info_added"] == 2
    assert db_session.query(Contact).count() == 2


# ---------------------------------------------------------------------------
# Validation / error cases
# ---------------------------------------------------------------------------

def test_import_rejects_non_csv_extension(client):
    r = client.post(
        "/api/contacts/import-csv",
        files={"file": ("contacts.xlsx", io.BytesIO(b"name\nAlice"), "application/octet-stream")},
    )
    assert r.status_code == 400
    assert "csv" in r.json()["detail"].lower()


def test_import_rejects_missing_name_column(client):
    csv = "email,linkedin\nalice@example.com,linkedin.com/in/alice\n"
    r = client.post("/api/contacts/import-csv", files={"file": _csv_file(csv)})
    assert r.status_code == 400
    detail = r.json()["detail"].lower()
    assert "name" in detail


def test_import_name_only_csv(client, db_session):
    """CSV with only a name column and no info columns should still create contacts."""
    csv = "name\nAlice\nBob\n"
    r = client.post("/api/contacts/import-csv", files={"file": _csv_file(csv)})
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 2
    assert data["info_added"] == 0
    assert db_session.query(Contact).count() == 2


def test_import_single_row(client, db_session):
    csv = "name,email\nJane Doe,jane@example.com\n"
    r = client.post("/api/contacts/import-csv", files={"file": _csv_file(csv)})
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 1
    assert data["info_added"] == 1

    contact = db_session.query(Contact).first()
    assert contact.name == "Jane Doe"
    info = db_session.query(ContactInfo).filter_by(contact_id=contact.id).first()
    assert info.type == "email"
    assert info.value == "jane@example.com"
