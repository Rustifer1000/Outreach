"""Tests for mentions API."""
from datetime import UTC, datetime, timedelta

from app.models import Contact, Mention


def test_list_mentions_empty(client):
    r = client.get("/api/mentions")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["mentions"] == []


def test_list_mentions_with_data(client, db_session):
    c = Contact(name="Alice", category="AI Safety")
    db_session.add(c)
    db_session.commit()

    now = datetime.now(UTC)
    db_session.add(Mention(
        contact_id=c.id,
        source_type="news",
        title="Alice in the news",
        snippet="AI safety researcher Alice Smith...",
        published_at=now,
        created_at=now,
    ))
    db_session.commit()

    r = client.get("/api/mentions?days=7")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    m = data["mentions"][0]
    assert m["contact_name"] == "Alice"
    assert m["source_type"] == "news"
    assert m["title"] == "Alice in the news"


def test_list_mentions_filter_by_contact(client, db_session):
    c1 = Contact(name="Alice", category="AI")
    c2 = Contact(name="Bob", category="Tech")
    db_session.add_all([c1, c2])
    db_session.commit()

    now = datetime.now(UTC)
    db_session.add(Mention(contact_id=c1.id, source_type="news", title="A", published_at=now, created_at=now))
    db_session.add(Mention(contact_id=c2.id, source_type="news", title="B", published_at=now, created_at=now))
    db_session.commit()

    r = client.get(f"/api/mentions?contact_id={c1.id}")
    assert r.status_code == 200
    assert all(m["contact_id"] == c1.id for m in r.json()["mentions"])


def test_get_mention_by_id(client, db_session):
    c = Contact(name="Carol", category="AI")
    db_session.add(c)
    db_session.commit()

    m = Mention(
        contact_id=c.id,
        source_type="podcast",
        title="Carol on podcast",
        snippet="Discussion about alignment",
        published_at=datetime.now(UTC),
    )
    db_session.add(m)
    db_session.commit()

    r = client.get(f"/api/mentions/{m.id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Carol on podcast"
    assert r.json()["source_type"] == "podcast"


def test_get_mention_not_found(client):
    r = client.get("/api/mentions/9999")
    assert r.status_code == 404


def test_list_mentions_old_excluded(client, db_session):
    """Mentions older than the requested window should be excluded."""
    c = Contact(name="Dave", category="Policy")
    db_session.add(c)
    db_session.commit()

    old = datetime.now(UTC) - timedelta(days=30)
    db_session.add(Mention(
        contact_id=c.id,
        source_type="news",
        title="Old mention",
        published_at=old,
        created_at=old,
    ))
    db_session.commit()

    r = client.get("/api/mentions?days=7")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_mentions_include_relevance_score(client, db_session):
    c = Contact(name="Eve", category="AI Safety")
    db_session.add(c)
    db_session.commit()

    db_session.add(Mention(
        contact_id=c.id,
        source_type="news",
        title="Eve mentioned",
        published_at=datetime.now(UTC),
        relevance_score=0.75,
    ))
    db_session.commit()

    r = client.get(f"/api/mentions?contact_id={c.id}")
    assert r.status_code == 200
    assert r.json()["mentions"][0]["relevance_score"] == 0.75
