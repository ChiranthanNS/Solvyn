from sqlalchemy.orm import Session
from datetime import date, datetime, time, timedelta
from sqlalchemy.exc import IntegrityError
from .models import (
    User,
    DiaryEntry,
    ConversationMessage,
    ConversationSummary,
    utc_now_naive,
)
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


def create_google_user(db: Session, email: str):
    new_user = User(
        email=email.strip().lower(),
        hashed_password="google_oauth",
        auth_provider="google",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    # Google users cannot login with password
    if user.auth_provider == "google" or user.hashed_password == "google_oauth":
        return None
    # Earlier Google-created users stored a bcrypt hash of this placeholder.
    # Reject the known placeholder rather than allowing it as a password.
    if verify_password("google_oauth", user.hashed_password):
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# -------------------------
# DIARY CRUD
# -------------------------

def create_diary_entry(
    db: Session,
    user_id: int,
    content: str,
    title: str | None = None,
    mood: str | None = None,
    entry_type: str = "user",
    summary_day: date | None = None,
):
    entry = DiaryEntry(
        user_id=user_id,
        title=title,
        content=content,
        mood=mood,
        entry_type=entry_type,
        summary_day=summary_day,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_diary_entries(
    db: Session,
    user_id: int,
    q: str | None = None,
    mood: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 200,
    offset: int = 0,
):
    query = db.query(DiaryEntry).filter(DiaryEntry.user_id == user_id)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(
            (DiaryEntry.content.ilike(pattern)) | (DiaryEntry.title.ilike(pattern))
        )
    if mood:
        query = query.filter(DiaryEntry.mood == mood)
    if date_from:
        query = query.filter(
            DiaryEntry.created_at >= datetime.combine(date_from, time.min)
        )
    if date_to:
        query = query.filter(
            DiaryEntry.created_at < datetime.combine(date_to + timedelta(days=1), time.min)
        )
    return query.order_by(DiaryEntry.created_at.desc()).offset(offset).limit(limit).all()


def get_diary_entry(db: Session, user_id: int, entry_id: int):
    return (
        db.query(DiaryEntry)
        .filter(DiaryEntry.id == entry_id, DiaryEntry.user_id == user_id)
        .first()
    )


def update_diary_entry(db: Session, entry: DiaryEntry, updates: schemas.DiaryUpdate):
    for field in updates.model_fields_set:
        setattr(entry, field, getattr(updates, field))
    db.commit()
    db.refresh(entry)
    return entry


def delete_diary_entry(db: Session, entry: DiaryEntry):
    db.delete(entry)
    db.commit()


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
            timestamp=utc_now_naive(),
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


def get_summary_candidate_day(db: Session, user_id: int, today: date) -> date | None:
    """Retry failed or abandoned days first, then find the latest prior UTC chat day."""
    stale_before = utc_now_naive() - timedelta(minutes=10)
    failed = (
        db.query(ConversationSummary)
        .filter(
            ConversationSummary.user_id == user_id,
            ConversationSummary.summary_day < today,
            (
                (ConversationSummary.status == "failed")
                | (
                    (ConversationSummary.status == "pending")
                    & (ConversationSummary.updated_at < stale_before)
                )
            ),
        )
        .order_by(ConversationSummary.summary_day.asc())
        .first()
    )
    if failed:
        return failed.summary_day

    today_start = datetime.combine(today, time.min)
    last_message = (
        db.query(ConversationMessage.timestamp)
        .filter(
            ConversationMessage.user_id == user_id,
            ConversationMessage.sender == "user",
            ConversationMessage.timestamp < today_start,
        )
        .order_by(ConversationMessage.timestamp.desc())
        .first()
    )
    if not last_message:
        return None
    candidate = last_message[0].date()
    marker = (
        db.query(ConversationSummary)
        .filter(
            ConversationSummary.user_id == user_id,
            ConversationSummary.summary_day == candidate,
        )
        .first()
    )
    if marker:
        return None
    return candidate


def claim_summary_day(db: Session, user_id: int, summary_day: date) -> bool:
    """Atomically claim a daily summary, allowing a failed claim to be retried."""
    marker = (
        db.query(ConversationSummary)
        .filter(
            ConversationSummary.user_id == user_id,
            ConversationSummary.summary_day == summary_day,
        )
        .first()
    )
    if marker:
        if marker.status != "failed":
            return False
        changed = (
            db.query(ConversationSummary)
            .filter(
                ConversationSummary.id == marker.id,
                ConversationSummary.status == marker.status,
            )
            .update({"status": "pending", "updated_at": utc_now_naive()})
        )
        db.commit()
        return changed == 1
    db.add(
        ConversationSummary(
            user_id=user_id,
            summary_day=summary_day,
            status="pending",
        )
    )
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def set_summary_status(db: Session, user_id: int, summary_day: date, status: str) -> None:
    marker = (
        db.query(ConversationSummary)
        .filter(
            ConversationSummary.user_id == user_id,
            ConversationSummary.summary_day == summary_day,
        )
        .first()
    )
    if marker:
        marker.status = status
        marker.updated_at = utc_now_naive()
        db.commit()


def get_existing_chat_summary(db: Session, user_id: int, summary_day: date):
    return (
        db.query(DiaryEntry)
        .filter(
            DiaryEntry.user_id == user_id,
            DiaryEntry.entry_type == "chat_summary",
            DiaryEntry.summary_day == summary_day,
        )
        .first()
    )


def get_conversation_day(db: Session, user_id: int, summary_day: date):
    start = datetime.combine(summary_day, time.min)
    end = datetime.combine(summary_day + timedelta(days=1), time.min)
    return (
        db.query(ConversationMessage)
        .filter(
            ConversationMessage.user_id == user_id,
            ConversationMessage.timestamp >= start,
            ConversationMessage.timestamp < end,
        )
        .order_by(ConversationMessage.timestamp.asc())
        .all()
    )
