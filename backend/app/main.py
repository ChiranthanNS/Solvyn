# app/main.py

import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel, ValidationError

from app.database import Base, engine, get_db
from app import schemas, crud
from app.auth import verify_token
from app.ai import generate_solution
from app.ai import API_KEY as GEMINI_API_KEY

# Routers
from app.routes.auth import router as auth_router
from app.routes.auth_google import router as google_router

# AI
from app.ai import summarize_text, detect_mood, safe_generate, generate_diary_summary
from datetime import datetime, time
from app.models import ConversationMessage

# ------------------------------------------------
# CREATE APP
# ------------------------------------------------
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Solvyn Backend")
WEB_DIR = Path(__file__).resolve().parents[2] / "web"

# ------------------------------------------------
# CORS
# ------------------------------------------------
allowed_origins = {
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
}
allowed_origins.update({"http://localhost:5000", "http://127.0.0.1:5000"})
for domain_key in ("REPLIT_DEV_DOMAIN", "REPLIT_DOMAINS"):
    for domain in os.getenv(domain_key, "").split(","):
        domain = domain.strip()
        if domain:
            allowed_origins.add(f"https://{domain}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------
# ROUTERS
# ------------------------------------------------
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(google_router, prefix="/auth", tags=["Google Auth"])

@app.get("/health")
def health():
    return {"status": "ok", "ai_configured": bool(GEMINI_API_KEY)}

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

    if not payload or not payload.get("user_id"):
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
def ai_summary(req: SummaryRequest, user_id: int = Depends(get_current_user)):
    return {"summary": summarize_text(req.text)}

# ------------------------------------------------
# AI MOOD
# ------------------------------------------------
class MoodRequest(BaseModel):
    text: str

@app.post("/ai/mood")
def ai_mood(req: MoodRequest, user_id: int = Depends(get_current_user)):
    return {"mood": detect_mood(req.text)}

# ------------------------------------------------
# PROBLEM SOLVING
# ------------------------------------------------
@app.post("/ai/solve", response_model=schemas.SolutionResponse)
def ai_solve(
    request: schemas.SolutionRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    started_at = time.perf_counter()
    solution = generate_solution(request.content)
    token_usage = solution.pop("_token_usage", None)
    solution["elapsed_seconds"] = round(time.perf_counter() - started_at, 2)
    solution["token_usage"] = token_usage

    try:
        response = schemas.SolutionResponse.model_validate(solution)
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail="The AI provider returned an incomplete solution.") from exc

    node_ids = {node.id for node in response.tree}
    if not response.tree or any(
        node.parent_id is not None and node.parent_id not in node_ids
        for node in response.tree
    ):
        raise HTTPException(status_code=502, detail="The AI provider returned an invalid solution tree.")

    crud.save_message(db, user_id, "user", request.content)
    crud.save_message(db, user_id, "ai", response.model_dump_json())
    return response

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
                    f"{date_str}\n\n{diary_content}"
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


# Serve the browser app after API routes so it cannot shadow them.
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
