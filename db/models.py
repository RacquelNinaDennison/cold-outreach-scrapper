import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from db.session import Base


class PersonalTrainer(Base):
    __tablename__ = "personal_trainers"
    __table_args__ = (
        UniqueConstraint("gym_slug", "profile_url", name="uq_gym_profile"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    gym_name = Column(String, nullable=False)
    gym_slug = Column(String, nullable=False)
    location = Column(String, nullable=False)
    suburb = Column(String, nullable=True)
    qualifications = Column(ARRAY(String), nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    instagram_handle = Column(String, nullable=True)
    facebook_url = Column(String, nullable=True)
    whatsapp_number = Column(String, nullable=True)
    profile_url = Column(String, nullable=False)
    profile_image_url = Column(String, nullable=True)
    scraped_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    outreach_emails = relationship("OutreachEmail", back_populates="pt_profile")


class OutreachEmail(Base):
    __tablename__ = "outreach_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pt_profile_id = Column(
        UUID(as_uuid=True), ForeignKey("personal_trainers.id"), nullable=False
    )
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    generated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    sent_at = Column(DateTime(timezone=True), nullable=True)

    pt_profile = relationship("PersonalTrainer", back_populates="outreach_emails")
