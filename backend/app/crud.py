from sqlalchemy.orm import Session
from datetime import datetime
from .models import User, DiaryEntry, ConversationMessage
from . import schemas
from .auth import hash_password, verify_password


# -------------------------
# USER CRUD
# -------------------------

def get_user(db: Session, user_id: int):
    """Fetch user by ID (required for token authentication)."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed = hash_password(user.password)
    new_user = User(email=user.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    # Google users cannot login with password
    if user.hashed_password == "google_oauth":
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# -------------------------
# DIARY CRUD
# -------------------------

def create_diary_entry(db: Session, user_id: int, content: str):
    entry = DiaryEntry(user_id=user_id, content=content)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_diary_entries(db: Session, user_id: int):
    return (
        db.query(DiaryEntry)
        .filter(DiaryEntry.user_id == user_id)
        .order_by(DiaryEntry.created_at.desc())
        .all()
    )


def get_recent_diary_summaries(db: Session, user_id: int, limit: int = 7) -> list[str]:
    """Fetch the last `limit` diary entries to use as long-term memory context."""
    entries = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.user_id == user_id)
        .order_by(DiaryEntry.created_at.desc())
        .limit(limit)
        .all()
    )
    return [e.content for e in reversed(entries)]


# -------------------------
# CONVERSATION CRUD
# -------------------------

def save_message(db: Session, user_id: int, sender: str, message: str):
    msg = ConversationMessage(
        user_id=user_id,
        sender=sender,
        message=message,
        timestamp=datetime.utcnow(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_conversation_history(db: Session, user_id: int, limit: int = 20):
    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.user_id == user_id)
        .order_by(ConversationMessage.timestamp.desc())
        .limit(limit)
        .all()
    )
    return messages[::-1]
