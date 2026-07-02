# app/main.py

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import Base, engine, get_db
from app import schemas, crud
from app.auth import verify_token

# Routers
from app.routes.auth import router as auth_router
from app.routes.auth_google import router as google_router

# AI
from app.ai import summarize_text, detect_mood, model, safe_generate, generate_diary_summary
from datetime import datetime, time
from app.models import ConversationMessage

# ------------------------------------------------
# CREATE APP
# ------------------------------------------------
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Solvyn Backend")

# ------------------------------------------------
# CORS
# ------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------
# ROUTERS
# ------------------------------------------------
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(google_router, prefix="/auth", tags=["Google Auth"])

# ------------------------------------------------
# HOME
# ------------------------------------------------
@app.get("/")
def home():
    return {"message": "Solvyn backend is running successfully!"}

# ------------------------------------------------
# AUTH DEPENDENCY
# ------------------------------------------------
def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.replace("Bearer ", "")
    payload = verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = crud.get_user(db, payload["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user.id

# ------------------------------------------------
# DIARY
# ------------------------------------------------
@app.post("/diary", response_model=schemas.DiaryResponse)
def create_diary(
    entry: schemas.DiaryCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    return crud.create_diary_entry(db, user_id, entry.content)

@app.get("/diary", response_model=list[schemas.DiaryResponse])
def get_diary(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    return crud.get_diary_entries(db, user_id)

# ------------------------------------------------
# AI SUMMARY
# ------------------------------------------------
class SummaryRequest(BaseModel):
    text: str

@app.post("/ai/summary")
def ai_summary(req: SummaryRequest):
    return {"summary": summarize_text(req.text)}

# ------------------------------------------------
# AI MOOD
# ------------------------------------------------
class MoodRequest(BaseModel):
    text: str

@app.post("/ai/mood")
def ai_mood(req: MoodRequest):
    return {"mood": detect_mood(req.text)}

# ------------------------------------------------
# AI CHAT
# ------------------------------------------------
@app.post("/ai/chat")
def ai_chat(
    request: schemas.ConversationMessageCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    # --- AUTO DIARY SUMMARY ---
    last_msg = db.query(ConversationMessage).filter(
        ConversationMessage.user_id == user_id,
        ConversationMessage.sender == "user"
    ).order_by(ConversationMessage.timestamp.desc()).first()

    current_date = datetime.utcnow().date()
    if last_msg and last_msg.timestamp.date() < current_date:
        last_day = last_msg.timestamp.date()
        start_of_day = datetime.combine(last_day, time.min)
        end_of_day = datetime.combine(last_day, time.max)

        old_msgs = db.query(ConversationMessage).filter(
            ConversationMessage.user_id == user_id,
            ConversationMessage.timestamp >= start_of_day,
            ConversationMessage.timestamp <= end_of_day
        ).order_by(ConversationMessage.timestamp.asc()).all()

        if old_msgs:
            conv_text = "\n".join([
                f"{'You' if m.sender == 'user' else 'Solvyn'}: {m.message}"
                for m in old_msgs
            ])
            date_str = last_day.strftime("%B %d, %Y")
            diary_content = generate_diary_summary(conv_text[-4000:], date_str)

            if diary_content:
                crud.create_diary_entry(
                    db, user_id,
                    f"\u{1F4C5} {date_str}\n\n{diary_content}"
                )
    # --------------------------

    crud.save_message(db, user_id, "user", request.content)

    mood = detect_mood(request.content)

    # --- TODAY'S CHAT (short-term memory) ---
    history = crud.get_conversation_history(db, user_id, limit=30)
    today_chat = ""
    for msg in history:
        role = "You" if msg.sender == "user" else "Solvyn"
        today_chat += f"{role}: {msg.message}\n"
    today_chat = today_chat[-2500:]

    # --- PAST DIARY ENTRIES (long-term memory) ---
    past_summaries = crud.get_recent_diary_summaries(db, user_id, limit=7)
    long_term_memory = ""
    if past_summaries:
        long_term_memory = "Here's what you know about your friend from past days:\n"
        for i, summary in enumerate(past_summaries, 1):
            long_term_memory += f"\n[Day {i} memory]\n{summary[:500]}\n"

    # --- FRIEND-LIKE PROMPT ---
    prompt = f"""You are Solvyn - not an AI assistant, but a genuine best friend who happens to be incredibly smart and emotionally aware.

Your personality:
- You talk like a real friend: casual, warm, sometimes funny, always honest
- You use contractions (you're, that's, I've, let's)
- You DON'T say "I understand" or "Certainly!" - you just respond naturally
- You remember what your friend has been through (from the memories below)
- When they're sad, you don't lecture - you just listen and be there
- When they're excited, you match their energy
- Keep replies to 2-4 sentences max unless they're clearly asking for more

Your friend's current mood: {mood}

{long_term_memory}

Today's conversation so far:
{today_chat}

Your friend just said: {request.content}

Solvyn (reply as their best friend):"""

    ai_reply = safe_generate(prompt).strip()

    if not ai_reply:
        ai_reply = "Hey, I'm here - what's going on?"

    crud.save_message(db, user_id, "ai", ai_reply)

    return {"reply": ai_reply, "mood": mood}

# ------------------------------------------------
# CHAT HISTORY
# ------------------------------------------------
@app.get("/ai/chat/history", response_model=list[schemas.ConversationMessageResponse])
def get_chat_history(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    return crud.get_conversation_history(db, user_id, limit=200)
