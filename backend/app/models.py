from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime, timezone


def utc_now_naive() -> datetime:
    """Store timestamps as naive UTC for compatibility with the existing schema."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# -----------------------------
# USER MODEL
# -----------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    auth_provider = Column(String(16), nullable=False, default="password", server_default="password")

    diary_entries = relationship(
        "DiaryEntry",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    conversation_messages = relationship(
        "ConversationMessage",
        back_populates="user",
        cascade="all, delete-orphan"
    )


# -----------------------------
# DIARY ENTRY MODEL
# -----------------------------
class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(160), nullable=True)
    content = Column(Text, nullable=False)
    mood = Column(String(16), nullable=True)
    entry_type = Column(String(24), nullable=False, default="user", server_default="user")
    summary_day = Column(Date, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive, nullable=False)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    user = relationship("User", back_populates="diary_entries")


# -----------------------------
# CHAT MESSAGE MODEL
# -----------------------------
class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender = Column(String, nullable=False)  # "user" or "ai"
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=utc_now_naive)

    user = relationship("User", back_populates="conversation_messages")


class ConversationSummary(Base):
    """Database-backed claim that prevents duplicate daily chat summaries."""

    __tablename__ = "conversation_summaries"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "summary_day", name="uq_conversation_summary_user_day"
        ),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    summary_day = Column(Date, nullable=False)
    status = Column(String(16), nullable=False, default="pending")
    created_at = Column(DateTime, default=utc_now_naive, nullable=False)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

