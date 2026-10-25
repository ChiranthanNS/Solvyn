# solvyn_app/ai.py

import json
import os

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
else:
    model = None


def _require_model():
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="AI is not configured. Add GEMINI_API_KEY to the app's secrets.",
        )
    return model


def safe_generate(prompt: str) -> str:
    """Generate text while returning clear, non-sensitive provider errors."""
    try:
        response = _require_model().generate_content(prompt, request_options={"timeout": 30})
        if not response or not response.text:
            raise HTTPException(status_code=502, detail="The AI provider returned an empty response.")
        return response.text.strip()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The AI provider request failed.") from exc


def generate_solution(prompt: str) -> dict:
    """Generate a structured, inspectable problem-solving response."""
    instructions = f"""You are Solvyn, a precise problem-solving assistant.
Analyze the user's problem and return ONLY a valid JSON object with this shape:
{{
  "title": "short problem title",
  "summary": "concise answer overview",
  "analysis": ["important observation"],
  "steps": [{{"title": "step title", "description": "what to do and why"}}],
  "tree": [{{"id": "root", "label": "Problem", "parent_id": null, "description": "problem statement"}}],
  "code_language": "python or null",
  "code": "illustrative code or null",
  "formula": "relevant formula or null",
  "complexity": "Low, Medium, or High",
  "related_tools": ["relevant tool or technique"]
}}
The tree must contain a root and useful child nodes whose parent_id refers to an existing node.
Do not claim code was executed or results were independently verified. Do not include markdown
fences. Keep the response actionable and accurate. Omit code and formula by using null when
they are not relevant.

User problem:
{prompt}"""
    try:
        response = _require_model().generate_content(
            instructions,
            generation_config={"response_mime_type": "application/json", "temperature": 0.35},
            request_options={"timeout": 30},
        )
        if not response or not response.text:
            raise HTTPException(status_code=502, detail="The AI provider returned an empty response.")
        result = json.loads(response.text)
        if not isinstance(result, dict):
            raise ValueError("The AI response was not a JSON object.")
        usage = getattr(response, "usage_metadata", None)
        result["_token_usage"] = getattr(usage, "total_token_count", None)
        return result
    except HTTPException:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="The AI provider returned an invalid solution.") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The AI provider request failed.") from exc


# ------------------------------------------------
# TEXT SUMMARY
# ------------------------------------------------
def summarize_text(text: str) -> str:
    prompt = f"""
    Summarize this diary entry in 2-3 warm, emotionally aware sentences.
    Write it like you're a close friend reflecting on their day.

    Diary Entry:
    {text}
    """
    return safe_generate(prompt)


# ------------------------------------------------
# MOOD DETECTION
# ------------------------------------------------
def detect_mood(text: str) -> str:
    prompt = f"""
    Read the following message and classify the emotional mood.
    Allowed moods: happy, sad, stressed, angry, excited, confused, neutral.
    Output ONLY ONE WORD with no punctuation.

    Message:
    {text}
    """

    mood = safe_generate(prompt).lower().strip().strip("`*_.,:;! ")

    allowed = [
        "happy", "sad", "stressed", "angry",
        "excited", "confused", "neutral"
    ]

    if mood in allowed:
        return mood
    raise HTTPException(status_code=502, detail="The AI provider returned an invalid mood.")


# ------------------------------------------------
# DIARY SUMMARY GENERATION
# Used at end-of-day to write a rich diary entry from the day's chat
# ------------------------------------------------
def generate_diary_summary(conversation_text: str, date_str: str) -> str:
    prompt = f"""
You are Solvyn, a close and caring friend. Based on the conversation below from {date_str},
write a warm, personal diary entry FROM THE USER'S PERSPECTIVE (write in first person: "Today I...").

Rules:
- Sound like a real personal diary, not a report
- Capture the emotions, key topics, and any breakthroughs or struggles
- Keep it between 3-5 sentences
- Do NOT start with "Dear Diary". Just dive straight in.

Conversation:
{conversation_text}

Diary Entry:
"""
    return safe_generate(prompt)
