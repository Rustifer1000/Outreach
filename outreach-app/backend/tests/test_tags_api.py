"""Tests for tags CRUD API and preset tags."""
from app.models import Contact


def test_get_preset_tags(client):
    r = client.get("/api/contacts/tags/preset")
    assert r.status_code == 200
    tags = r.json()["tags"]
    assert isinstance(tags, list)
    assert len(tags) >= 6
    assert "Prioritize" in tags
    assert "Warm intro available" in tags


def test_add_tag(client, db_session):
    db_session.add(Contact(name="Alice", category="AI Safety"))
    db_session.commit()
    cid = db_session.query(Contact.id).scalar()

    r = client.post(f"/api/contacts/{cid}/tags", json={"tag": "Prioritize"})
    assert r.status_code == 200
    assert r.json()["tag"] == "Prioritize"
    assert "id" in r.json()


def test_add_duplicate_tag(client, db_session):
    db_session.add(Contact(name="Bob", category="Tech"))
    db_session.commit()
    cid = db_session.query(Contact.id).scalar()

    client.post(f"/api/contacts/{cid}/tags", json={"tag": "Prioritize"})
    r2 = client.post(f"/api/contacts/{cid}/tags", json={"tag": "Prioritize"})
    assert r2.status_code == 200
    assert "already exists" in r2.json().get("message", "")


def test_add_empty_tag(client, db_session):
    db_session.add(Contact(name="Carol", category="AI"))
    db_session.commit()
    cid = db_session.query(Contact.id).scalar()

    r = client.post(f"/api/contacts/{cid}/tags", json={"tag": "   "})
    assert r.status_code == 400


def test_list_tags(client, db_session):
    db_session.add(Contact(name="Dave", category="Policy"))
    db_session.commit()
    cid = db_session.query(Contact.id).scalar()

    client.post(f"/api/contacts/{cid}/tags", json={"tag": "Tag1"})
    client.post(f"/api/contacts/{cid}/tags", json={"tag": "Tag2"})

    r = client.get(f"/api/contacts/{cid}/tags")
    assert r.status_code == 200
    tags = r.json()["tags"]
    assert len(tags) == 2
    assert {t["tag"] for t in tags} == {"Tag1", "Tag2"}


def test_delete_tag(client, db_session):
    db_session.add(Contact(name="Eve", category="AI Safety"))
    db_session.commit()
    cid = db_session.query(Contact.id).scalar()

    r = client.post(f"/api/contacts/{cid}/tags", json={"tag": "ToRemove"})
    tag_id = r.json()["id"]

    r2 = client.delete(f"/api/contacts/{cid}/tags/{tag_id}")
    assert r2.status_code == 200
    assert r2.json()["ok"] is True

    # Verify gone
    r3 = client.get(f"/api/contacts/{cid}/tags")
    assert len(r3.json()["tags"]) == 0


def test_delete_nonexistent_tag(client, db_session):
    db_session.add(Contact(name="Frank", category="Tech"))
    db_session.commit()
    cid = db_session.query(Contact.id).scalar()

    r = client.delete(f"/api/contacts/{cid}/tags/9999")
    assert r.status_code == 404


def test_tags_appear_in_contact_list(client, db_session):
    db_session.add(Contact(name="Grace", category="AI Policy"))
    db_session.commit()
    cid = db_session.query(Contact.id).scalar()

    client.post(f"/api/contacts/{cid}/tags", json={"tag": "Funding potential"})

    r = client.get("/api/contacts")
    contacts = r.json()["contacts"]
    assert len(contacts) == 1
    assert "Funding potential" in contacts[0]["tags"]


def test_tags_appear_in_contact_detail(client, db_session):
    db_session.add(Contact(name="Helen", category="AI Safety"))
    db_session.commit()
    cid = db_session.query(Contact.id).scalar()

    client.post(f"/api/contacts/{cid}/tags", json={"tag": "Already engaged"})

    r = client.get(f"/api/contacts/{cid}")
    assert r.status_code == 200
    assert "Already engaged" in r.json()["tags"]
