"""Tests for warm intro paths, mission alignment, and auto-tagging."""
from app.models import Contact, ContactConnection, ContactTag, OutreachLog
from app.warm_intros import (
    compute_mission_alignment,
    find_warm_intro_paths,
    auto_tag_warm_intro,
    PRESET_TAGS,
    CATEGORY_ALIGNMENT,
)


# --- Mission alignment ---


def test_alignment_ai_safety():
    """AI safety category should score high."""
    c = Contact(name="Test", category="AI Safety")
    score = compute_mission_alignment(c)
    assert score >= 9.0


def test_alignment_default():
    """No category = default 5.0."""
    c = Contact(name="Test")
    score = compute_mission_alignment(c)
    assert score == 5.0


def test_alignment_business():
    """Business category should score low."""
    c = Contact(name="Test", category="Business")
    score = compute_mission_alignment(c)
    assert score <= 5.0


def test_alignment_connection_boost():
    """Direct connection to Solomon should boost score."""
    c = Contact(name="Test", category="AI Policy", connection_to_solomon="Direct advisor")
    score = compute_mission_alignment(c)
    # AI policy = 8.0 + direct connection = +1.0
    assert score >= 9.0


def test_alignment_interests_boost():
    """AI safety interests should boost score."""
    c = Contact(name="Test", category="Media", primary_interests="Covers AI safety and existential risk")
    score = compute_mission_alignment(c)
    # Media = 5.5, interests boost = +1.0
    assert score >= 6.0


def test_alignment_max_10():
    """Score should be capped at 10.0."""
    c = Contact(
        name="Test",
        category="AI Safety",
        connection_to_solomon="Direct board member",
        primary_interests="AI safety, alignment, x-risk",
    )
    score = compute_mission_alignment(c)
    assert score <= 10.0


# --- Warm intro paths ---


def test_warm_intros_no_connections(db_session):
    """Contact with no connections = no intro paths."""
    c = Contact(name="Target")
    db_session.add(c)
    db_session.commit()

    paths = find_warm_intro_paths(db_session, c.id)
    assert paths == []


def test_warm_intros_basic(db_session):
    """Basic warm intro: connector has first_degree connection to target."""
    target = Contact(name="Target", category="AI Safety")
    connector = Contact(name="Connector", relationship_stage="Engaged")
    db_session.add_all([target, connector])
    db_session.commit()

    db_session.add(ContactConnection(
        contact_id=target.id,
        other_contact_id=connector.id,
        relationship_type="first_degree",
    ))
    db_session.commit()

    paths = find_warm_intro_paths(db_session, target.id)
    assert len(paths) == 1
    assert paths[0]["connector_name"] == "Connector"
    assert paths[0]["connector_stage"] == "Engaged"
    assert paths[0]["intro_strength"] > 0


def test_warm_intros_ranked_by_stage(db_session):
    """Engaged connector should rank higher than Cold connector."""
    target = Contact(name="Target")
    engaged = Contact(name="Engaged Friend", relationship_stage="Engaged")
    cold = Contact(name="Cold Contact", relationship_stage="Cold")
    db_session.add_all([target, engaged, cold])
    db_session.commit()

    db_session.add(ContactConnection(
        contact_id=target.id, other_contact_id=engaged.id, relationship_type="first_degree",
    ))
    db_session.add(ContactConnection(
        contact_id=target.id, other_contact_id=cold.id, relationship_type="first_degree",
    ))
    db_session.commit()

    paths = find_warm_intro_paths(db_session, target.id)
    assert len(paths) == 2
    assert paths[0]["connector_name"] == "Engaged Friend"
    assert paths[0]["intro_strength"] > paths[1]["intro_strength"]


def test_warm_intros_replied_bonus(db_session):
    """Connector who has replied should get a bonus."""
    target = Contact(name="Target")
    replied = Contact(name="Replied", relationship_stage="Warm")
    silent = Contact(name="Silent", relationship_stage="Warm")
    db_session.add_all([target, replied, silent])
    db_session.commit()

    db_session.add(ContactConnection(
        contact_id=target.id, other_contact_id=replied.id, relationship_type="first_degree",
    ))
    db_session.add(ContactConnection(
        contact_id=target.id, other_contact_id=silent.id, relationship_type="first_degree",
    ))
    db_session.add(OutreachLog(
        contact_id=replied.id, method="email", response_status="replied",
    ))
    db_session.commit()

    paths = find_warm_intro_paths(db_session, target.id)
    assert len(paths) == 2
    replied_path = [p for p in paths if p["connector_name"] == "Replied"][0]
    silent_path = [p for p in paths if p["connector_name"] == "Silent"][0]
    assert replied_path["has_replied"] is True
    assert replied_path["intro_strength"] > silent_path["intro_strength"]


def test_warm_intros_nonexistent_contact(db_session):
    """Nonexistent target ID should return empty list."""
    paths = find_warm_intro_paths(db_session, 9999)
    assert paths == []


# --- Warm intro API ---


def test_warm_intros_api(client, db_session):
    target = Contact(name="Target", category="AI Safety")
    connector = Contact(name="Connector", relationship_stage="Partner-Advocate")
    db_session.add_all([target, connector])
    db_session.commit()

    db_session.add(ContactConnection(
        contact_id=target.id, other_contact_id=connector.id, relationship_type="advisor",
    ))
    db_session.commit()

    r = client.get(f"/api/contacts/{target.id}/warm-intros")
    assert r.status_code == 200
    data = r.json()
    assert data["contact_name"] == "Target"
    assert data["count"] == 1
    assert data["intro_paths"][0]["connector_name"] == "Connector"


def test_warm_intros_api_not_found(client):
    r = client.get("/api/contacts/9999/warm-intros")
    assert r.status_code == 404


# --- Compute alignment API ---


def test_compute_alignment_api(client, db_session):
    c = Contact(name="Alice", category="AI Safety")
    db_session.add(c)
    db_session.commit()

    r = client.post(f"/api/contacts/{c.id}/compute-alignment")
    assert r.status_code == 200
    assert r.json()["mission_alignment"] >= 9.0


# --- Auto-tag warm intro ---


def test_auto_tag_warm_intro(db_session):
    """Auto-tag should tag contacts connected to engaged contacts."""
    target = Contact(name="Target", relationship_stage="Cold")
    engaged = Contact(name="Engaged", relationship_stage="Engaged")
    unconnected = Contact(name="Loner", relationship_stage="Cold")
    db_session.add_all([target, engaged, unconnected])
    db_session.commit()

    db_session.add(ContactConnection(
        contact_id=target.id, other_contact_id=engaged.id, relationship_type="first_degree",
    ))
    db_session.commit()

    result = auto_tag_warm_intro(db_session)
    assert result["tagged"] >= 1

    # Target should have the tag (connected to engaged)
    tags = db_session.query(ContactTag).filter(
        ContactTag.contact_id == target.id, ContactTag.tag == "Warm intro available"
    ).all()
    assert len(tags) == 1

    # Loner should NOT have the tag
    loner_tags = db_session.query(ContactTag).filter(
        ContactTag.contact_id == unconnected.id, ContactTag.tag == "Warm intro available"
    ).all()
    assert len(loner_tags) == 0


# --- Preset tags ---


def test_preset_tags_count():
    assert len(PRESET_TAGS) == 6


def test_preset_tags_content():
    assert "Funding potential" in PRESET_TAGS
    assert "Amplification potential" in PRESET_TAGS
