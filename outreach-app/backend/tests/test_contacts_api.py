"""Tests for contacts and rotation API."""
import pytest
from app.models import Contact


def test_list_contacts_empty(client):
    r = client.get("/api/contacts")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["contacts"] == []


def test_list_contacts_in_rotation_filter(client, db_session):
    db_session.add(Contact(name="Alice", category="Policy", in_mention_rotation=0))
    db_session.add(Contact(name="Bob", category="Tech", in_mention_rotation=1))
    db_session.add(Contact(name="Carol", category="Tech", in_mention_rotation=1))
    db_session.commit()

    r = client.get("/api/contacts")
    assert r.status_code == 200
    assert r.json()["total"] == 3

    r2 = client.get("/api/contacts?in_rotation=1")
    assert r2.status_code == 200
    data = r2.json()
    assert data["total"] == 2
    names = [c["name"] for c in data["contacts"]]
    assert "Bob" in names and "Carol" in names and "Alice" not in names


def test_rotation_get_empty(client):
    r = client.get("/api/contacts/rotation")
    assert r.status_code == 200
    assert r.json()["in_rotation"] == 0
    assert r.json()["contacts"] == []


def test_rotation_put_and_get(client, db_session):
    db_session.add(Contact(name="A", list_number=1, in_mention_rotation=0))
    db_session.add(Contact(name="B", list_number=2, in_mention_rotation=0))
    db_session.commit()
    ids = [c.id for c in db_session.query(Contact).all()]

    r = client.put("/api/contacts/rotation", json={"contact_ids": [ids[0]]})
    assert r.status_code == 200
    assert r.json()["in_rotation"] == 1

    r2 = client.get("/api/contacts/rotation")
    assert r2.status_code == 200
    assert len(r2.json()["contacts"]) == 1
    assert r2.json()["contacts"][0]["name"] == "A"

    r3 = client.put("/api/contacts/rotation", json={"contact_ids": ids})
    assert r3.json()["in_rotation"] == 2
    r4 = client.get("/api/contacts/rotation")
    assert len(r4.json()["contacts"]) == 2


def test_patch_in_mention_rotation(client, db_session):
    db_session.add(Contact(name="X", in_mention_rotation=0))
    db_session.commit()
    contact_id = db_session.query(Contact.id).scalar()

    r = client.patch(
        f"/api/contacts/{contact_id}",
        json={"in_mention_rotation": True},
    )
    assert r.status_code == 200
    assert r.json()["in_mention_rotation"] is True

    r2 = client.get("/api/contacts?in_rotation=1")
    assert r2.json()["total"] == 1
    assert r2.json()["contacts"][0]["name"] == "X"

    client.patch(f"/api/contacts/{contact_id}", json={"in_mention_rotation": False})
    r3 = client.get("/api/contacts?in_rotation=1")
    assert r3.json()["total"] == 0
