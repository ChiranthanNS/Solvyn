# app/main.py

import json
import os
import time as timing
import threading
from collections import defaultdict, deque
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Header, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.database import get_db
from app import schemas, crud
from app.auth import verify_token
from app.ai import generate_solution
from app.ai import API_KEY as GEMINI_API_KEY

# Routers
from app.routes.auth import router as auth_router
from app.routes.auth_google import router as google_router

# AI
from app.ai import summarize_text, detect_mood, safe_generate, generate_diary_summary
from app.models import ConversationMessage

# ------------------------------------------------
# CREATE APP
# ------------------------------------------------
app = FastAPI(title="Solvyn — Personal Diary and Reflection Companion")
WEB_DIR = Path(__file__).resolve().parents[2] / "web"

# ------------------------------------------------
# CORS
# ------------------------------------------------
allowed_origins = {
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
}
for domain_key in ("REPLIT_DEV_DOMAIN", "REPLIT_DOMAINS"):
    for domain in os.getenv(domain_key, "").split(","):
        domain = domain.strip()
        if domain:
            allowed_origins.add(f"https://{domain}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def sanitized_validation_error(_request, _exc: RequestValidationError):
    # Pydantic's default response includes the rejected input (which may be a password).
    return JSONResponse(status_code=422, content={"detail": "Request input is invalid."})

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
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token)

    user_id = payload.get("user_id") if payload else None
    if not isinstance(user_id, int) or isinstance(user_id, bool):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user.id


_AI_WINDOW_SECONDS = 60
_AI_REQUESTS_PER_WINDOW = 8
_ai_request_times: dict[int, deque[float]] = defaultdict(deque)
_ai_rate_lock = threading.Lock()


def check_ai_rate_limit(user_id: int) -> None:
    now = timing.monotonic()
    cutoff = now - _AI_WINDOW_SECONDS
    with _ai_rate_lock:
        requests = _ai_request_times[user_id]
        while requests and requests[0] <= cutoff:
            requests.popleft()
        if len(requests) >= _AI_REQUESTS_PER_WINDOW:
            retry_after = max(1, int(requests[0] + _AI_WINDOW_SECONDS - now))
            raise HTTPException(
                status_code=429,
                detail="Too many AI requests. Please wait a moment and try again.",
                headers={"Retry-After": str(retry_after)},
            )
        requests.append(now)

# ------------------------------------------------
# DIARY
# ------------------------------------------------
@app.post("/diary", response_model=schemas.DiaryResponse)
def create_diary(
    entry: schemas.DiaryCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    return crud.create_diary_entry(
        db, user_id, entry.content, title=entry.title, mood=entry.mood
    )

@app.get("/diary", response_model=list[schemas.DiaryResponse])
def get_diary(
    q: str | None = Query(default=None, max_length=160),
    mood: schemas.Mood | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=200, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to.")
    return crud.get_diary_entries(
        db,
        user_id,
        q=q,
        mood=mood,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@app.get("/diary/{entry_id}", response_model=schemas.DiaryResponse)
def get_diary_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    entry = crud.get_diary_entry(db, user_id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Diary entry not found.")
    return entry


@app.patch("/diary/{entry_id}", response_model=schemas.DiaryResponse)
def update_diary_entry(
    entry_id: int,
    entry_update: schemas.DiaryUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    entry = crud.get_diary_entry(db, user_id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Diary entry not found.")
    if not entry_update.model_fields_set:
        raise HTTPException(status_code=422, detail="Provide at least one field to update.")
    return crud.update_diary_entry(db, entry, entry_update)


@app.delete("/diary/{entry_id}", status_code=204)
def delete_diary_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    entry = crud.get_diary_entry(db, user_id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Diary entry not found.")
    crud.delete_diary_entry(db, entry)
    return Response(status_code=204)

# ------------------------------------------------
# AI REFLECTION
# ------------------------------------------------
@app.post("/ai/summary")
def ai_summary(
    req: schemas.SummaryRequest,
    user_id: int = Depends(get_current_user),
):
    check_ai_rate_limit(user_id)
    return {"summary": summarize_text(req.text)}


@app.post("/diary/{entry_id}/summary")
def summarize_diary_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    entry = crud.get_diary_entry(db, user_id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Diary entry not found.")
    check_ai_rate_limit(user_id)
    return {"summary": summarize_text(entry.content)}


# ------------------------------------------------
# AI MOOD
# ------------------------------------------------
@app.post("/ai/mood")
def ai_mood(req: schemas.MoodRequest, user_id: int = Depends(get_current_user)):
    check_ai_rate_limit(user_id)
    mood = detect_mood(req.text)
    if mood not in schemas.Mood.__args__:
        raise HTTPException(status_code=502, detail="The AI provider returned an invalid mood.")
    return {"mood": mood}

# ------------------------------------------------
# PROBLEM SOLVING
# ------------------------------------------------
@app.post("/ai/solve", response_model=schemas.SolutionResponse)
def ai_solve(
    request: schemas.SolutionRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    check_ai_rate_limit(user_id)
    started_at = timing.perf_counter()
    crud.save_message(db, user_id, "user", request.content)
    solution = generate_solution(request.content)
    token_usage = solution.pop("_token_usage", None)
    solution["elapsed_seconds"] = round(timing.perf_counter() - started_at, 2)
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

    crud.save_message(db, user_id, "ai", response.model_dump_json())
    return response

# ------------------------------------------------
# AI CHAT
# ------------------------------------------------
def maybe_create_daily_chat_summary(db: Session, user_id: int, today: date) -> None:
    summary_day = crud.get_summary_candidate_day(db, user_id, today)
    if summary_day is None:
        return
    if crud.get_existing_chat_summary(db, user_id, summary_day):
        crud.set_summary_status(db, user_id, summary_day, "complete")
        return
    if not crud.claim_summary_day(db, user_id, summary_day):
        return
    messages = crud.get_conversation_day(db, user_id, summary_day)
    if not messages:
        crud.set_summary_status(db, user_id, summary_day, "complete")
        return
    conversation = "\n".join(
        f"{'You' if message.sender == 'user' else 'Solvyn'}: {message.message}"
        for message in messages
    )
    try:
        content = generate_diary_summary(
            conversation[-4000:], summary_day.strftime("%B %d, %Y")
        ).strip()
        if not content:
            raise ValueError("The provider returned an empty summary.")
        if not crud.get_existing_chat_summary(db, user_id, summary_day):
            crud.create_diary_entry(
                db,
                user_id,
                content,
                title=f"Reflection for {summary_day.strftime('%B %d, %Y')}",
                entry_type="chat_summary",
                summary_day=summary_day,
            )
        crud.set_summary_status(db, user_id, summary_day, "complete")
    except Exception:
        # Summary generation is optional and must not prevent normal chat.
        crud.set_summary_status(db, user_id, summary_day, "failed")


@app.post("/ai/chat")
def ai_chat(
    request: schemas.ConversationMessageCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    check_ai_rate_limit(user_id)
    crud.save_message(db, user_id, "user", request.content)
    today = datetime.now(timezone.utc).date()
    maybe_create_daily_chat_summary(db, user_id, today)

    # Chat context is restricted to this user's current UTC day.
    history = crud.get_conversation_history(db, user_id, limit=100)
    start_of_today = datetime.combine(today, datetime_time.min)
    today_chat = ""
    for msg in history:
        if msg.timestamp < start_of_today:
            continue
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
- You offer reflection, not medical advice or diagnoses.

Respond to the emotions in the message without assigning a mood label or diagnosis.

{long_term_memory}

Today's conversation so far:
{today_chat}

Your friend just said: {request.content}

Solvyn (reply as their best friend):"""

    ai_reply = safe_generate(prompt).strip()

    if not ai_reply:
        raise HTTPException(status_code=502, detail="The AI provider returned an empty response.")

    crud.save_message(db, user_id, "ai", ai_reply)

    return {"reply": ai_reply, "mood": None}

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
