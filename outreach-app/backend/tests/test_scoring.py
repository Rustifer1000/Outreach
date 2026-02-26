"""Tests for the relevance scoring engine (app.scoring)."""
from datetime import UTC, datetime, timedelta

from app.models import Contact, Mention
from app.scoring import (
    _name_in_text,
    _disambiguation_score,
    score_mention,
    score_all_mentions,
    get_hot_leads,
    generate_daily_digest,
    SOURCE_TYPE_WEIGHTS,
    DEFAULT_SOURCE_WEIGHT,
)


# --- Unit tests for helper functions ---


def test_name_in_text_full_match():
    found, score = _name_in_text("John Smith", "Interview with John Smith on AI safety")
    assert found is True
    assert score == 1.0


def test_name_in_text_case_insensitive():
    found, score = _name_in_text("John Smith", "john smith discusses policy")
    assert found is True
    assert score == 1.0


def test_name_in_text_last_name_only():
    found, score = _name_in_text("John Smith", "Dr. Smith presented today")
    assert found is True
    assert score == 0.5


def test_name_in_text_not_found():
    found, score = _name_in_text("John Smith", "Completely unrelated article")
    assert found is False
    assert score == 0.0


def test_name_in_text_empty():
    found, score = _name_in_text("John Smith", "")
    assert found is False
    assert score == 0.0

    found2, score2 = _name_in_text("John Smith", None)
    assert found2 is False
    assert score2 == 0.0


def test_disambiguation_score_with_role_org_match():
    contact = Contact(name="Test", role_org="OpenAI, Research", category="AI Safety")
    score = _disambiguation_score(contact, "OpenAI researcher speaks", "AI safety conference")
    assert score > 0.5


def test_disambiguation_score_no_context():
    contact = Contact(name="Test")
    score = _disambiguation_score(contact, "Some title", "Some snippet")
    assert score == 0.5  # No context clues = neutral


def test_disambiguation_score_empty_text():
    contact = Contact(name="Test", role_org="OpenAI")
    score = _disambiguation_score(contact, None, None)
    assert score == 0.5  # No text to judge


def test_disambiguation_score_no_match():
    contact = Contact(name="Test", role_org="OpenAI Research", category="AI Safety")
    score = _disambiguation_score(contact, "Football game results", "Lakers win championship")
    assert score <= 0.3


# --- Score mention tests ---


def test_score_mention_podcast_recent():
    """A recent podcast mention of an AI safety person should score high."""
    contact = Contact(name="Alice Smith", category="AI Safety", role_org="MIRI")
    mention = Mention(
        contact_id=1,
        source_type="podcast",
        title="Alice Smith on AI alignment risks",
        snippet="Alice Smith from MIRI discusses alignment",
        published_at=datetime.now(UTC) - timedelta(hours=2),
    )
    score = score_mention(mention, contact)
    assert 0.5 < score <= 1.0


def test_score_mention_old_news():
    """An old news mention should score lower than a recent one."""
    contact = Contact(name="Bob Jones", category="Tech")
    recent = Mention(
        contact_id=1,
        source_type="news",
        title="Bob Jones interview",
        snippet="Tech leader Bob Jones",
        published_at=datetime.now(UTC) - timedelta(days=1),
    )
    old = Mention(
        contact_id=1,
        source_type="news",
        title="Bob Jones interview",
        snippet="Tech leader Bob Jones",
        published_at=datetime.now(UTC) - timedelta(days=25),
    )
    recent_score = score_mention(recent, contact)
    old_score = score_mention(old, contact)
    assert recent_score > old_score


def test_score_mention_source_type_weights():
    """Podcast should score higher than news, all else equal."""
    contact = Contact(name="Test Person", category="AI Safety", role_org="OpenAI")
    base = dict(
        contact_id=1,
        title="Test Person on AI safety",
        snippet="Test Person from OpenAI discusses safety",
        published_at=datetime.now(UTC),
    )
    podcast_score = score_mention(Mention(source_type="podcast", **base), contact)
    news_score = score_mention(Mention(source_type="news", **base), contact)
    assert podcast_score > news_score


def test_score_mention_name_in_title_boost():
    """Name in title should boost score vs name only in snippet."""
    contact = Contact(name="Jane Doe", category="AI Policy")
    in_title = Mention(
        contact_id=1,
        source_type="news",
        title="Jane Doe speaks at summit",
        snippet="Policy discussion",
        published_at=datetime.now(UTC),
    )
    not_in_title = Mention(
        contact_id=1,
        source_type="news",
        title="Policy summit recap",
        snippet="Jane Doe attended the event",
        published_at=datetime.now(UTC),
    )
    assert score_mention(in_title, contact) > score_mention(not_in_title, contact)


def test_score_mention_bounds():
    """Score should always be between 0.0 and 1.0."""
    contact = Contact(name="X", category="Unknown")
    mention = Mention(
        contact_id=1,
        source_type="unknown_type",
        title=None,
        snippet=None,
        published_at=datetime.now(UTC) - timedelta(days=100),
    )
    score = score_mention(mention, contact)
    assert 0.0 <= score <= 1.0


# --- score_all_mentions (DB-level) ---


def test_score_all_mentions(db_session):
    """score_all_mentions should store scores in the DB."""
    c = Contact(name="Alice", category="AI Safety", role_org="MIRI")
    db_session.add(c)
    db_session.commit()

    m1 = Mention(
        contact_id=c.id,
        source_type="podcast",
        title="Alice on alignment",
        snippet="MIRI researcher Alice discusses safety",
        published_at=datetime.now(UTC),
    )
    m2 = Mention(
        contact_id=c.id,
        source_type="news",
        title="AI Safety roundup",
        snippet="Alice from MIRI was mentioned",
        published_at=datetime.now(UTC) - timedelta(days=10),
    )
    db_session.add_all([m1, m2])
    db_session.commit()

    result = score_all_mentions(db_session)
    assert result["scored"] == 2
    assert result["skipped"] == 0

    # Verify scores stored
    db_session.expire_all()
    m1_fresh = db_session.query(Mention).filter(Mention.id == m1.id).first()
    m2_fresh = db_session.query(Mention).filter(Mention.id == m2.id).first()
    assert m1_fresh.relevance_score is not None
    assert m2_fresh.relevance_score is not None
    assert 0.0 <= m1_fresh.relevance_score <= 1.0


def test_score_all_mentions_skip_scored(db_session):
    """Already-scored mentions should be skipped unless rescore=True."""
    c = Contact(name="Bob", category="Tech")
    db_session.add(c)
    db_session.commit()

    m = Mention(
        contact_id=c.id,
        source_type="news",
        title="Bob in tech",
        published_at=datetime.now(UTC),
        relevance_score=0.5,
    )
    db_session.add(m)
    db_session.commit()

    result = score_all_mentions(db_session, rescore=False)
    assert result["scored"] == 0  # Already scored, skip

    result2 = score_all_mentions(db_session, rescore=True)
    assert result2["scored"] == 1  # Rescore forced


# --- Hot leads ---


def test_get_hot_leads_empty(db_session):
    """No mentions = no hot leads."""
    leads = get_hot_leads(db_session)
    assert leads == []


def test_get_hot_leads_with_data(db_session):
    """Contact with many recent mentions should appear as hot lead."""
    c = Contact(name="Hot Contact", category="AI Safety")
    db_session.add(c)
    db_session.commit()

    now = datetime.now(UTC)
    for i in range(3):
        db_session.add(Mention(
            contact_id=c.id,
            source_type=["news", "podcast", "video"][i],
            title=f"Mention {i}",
            published_at=now - timedelta(hours=i * 12),
            relevance_score=0.7,
        ))
    db_session.commit()

    leads = get_hot_leads(db_session, days=7, min_mentions=2)
    assert len(leads) >= 1
    assert leads[0]["contact_id"] == c.id
    assert leads[0]["mention_count"] == 3
    assert leads[0]["contact_name"] == "Hot Contact"
    assert "heat_score" in leads[0]


# --- Daily digest ---


def test_generate_daily_digest_empty(db_session):
    """Digest with no data should return structured result."""
    digest = generate_daily_digest(db_session, hours=24)
    assert "new_mentions" in digest
    assert "hot_leads" in digest
    assert "follow_up_due" in digest
    assert "low_confidence_mentions" in digest
    assert "summary" in digest
    assert digest["new_mentions"]["total"] == 0


def test_generate_daily_digest_with_mentions(db_session):
    """Digest should report new mentions."""
    c = Contact(name="Alice", category="AI Safety")
    db_session.add(c)
    db_session.commit()

    db_session.add(Mention(
        contact_id=c.id,
        source_type="news",
        title="Alice in the news",
        published_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    ))
    db_session.commit()

    digest = generate_daily_digest(db_session, hours=24)
    assert digest["new_mentions"]["total"] == 1
    assert digest["new_mentions"]["by_source_type"]["news"] == 1
