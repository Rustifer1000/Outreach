"""SQLAlchemy models for Phase 1 data model."""
from datetime import UTC, datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.database import Base


class Contact(Base):
    """Contact from the Solomon Influencer Flywheel List."""
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    list_number = Column(Integer, nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(255), nullable=True, index=True)
    subcategory = Column(String(255), nullable=True)
    role_org = Column(Text, nullable=True)
    connection_to_solomon = Column(Text, nullable=True)
    primary_interests = Column(Text, nullable=True)  # For future enrichment
    relationship_stage = Column(String(50), nullable=True)  # Cold, Warm, Engaged, Partner-Advocate
    in_mention_rotation = Column(Integer, default=0)  # 1 = include in daily mention fetch (tagged core group)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    mentions = relationship("Mention", back_populates="contact")
    outreach_log = relationship("OutreachLog", back_populates="contact")
    contact_info = relationship("ContactInfo", back_populates="contact")
    notes = relationship("Note", back_populates="contact")
    connections = relationship(
        "ContactConnection",
        back_populates="contact",
        foreign_keys="ContactConnection.contact_id",
    )


class ContactInfo(Base):
    """Contact info (email, LinkedIn, etc.)."""
    __tablename__ = "contact_info"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # email, linkedin, twitter, phone, etc.
    value = Column(String(500), nullable=False)
    is_primary = Column(Integer, default=0)  # 0 or 1
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    contact = relationship("Contact", back_populates="contact_info")


class Mention(Base):
    """News/media mention of a contact."""
    __tablename__ = "mentions"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # news, podcast, etc.
    source_url = Column(String(1000), nullable=True)
    title = Column(String(500), nullable=True)
    snippet = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    relevance_score = Column(Float, nullable=True)  # Phase 3
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    contact = relationship("Contact", back_populates="mentions")


class OutreachLog(Base):
    """Log of outreach attempts."""
    __tablename__ = "outreach_log"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    method = Column(String(50), nullable=False)  # email, linkedin, etc.
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    response_status = Column(String(50), nullable=True)  # sent, replied, no_response, bounced
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    contact = relationship("Contact", back_populates="outreach_log")


class Note(Base):
    """Conversation note for a contact (follow-ups, call notes, etc.)."""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    note_text = Column(Text, nullable=False)
    note_date = Column(DateTime, nullable=False)  # When the conversation/note occurred
    channel = Column(String(50), nullable=True)  # email, call, meeting, etc.
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    contact = relationship("Contact", back_populates="notes")


class ContactConnection(Base):
    """How this contact is related to others on the list (first/second degree, same org, co-author, etc.)."""
    __tablename__ = "contact_connections"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    other_contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    relationship_type = Column(String(100), nullable=False)  # first_degree, second_degree, same_org, co_author, etc.
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    contact = relationship("Contact", back_populates="connections", foreign_keys=[contact_id])
    other_contact = relationship("Contact", foreign_keys=[other_contact_id])
