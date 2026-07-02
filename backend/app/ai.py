# solvyn_app/ai.py

import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Read Gemini API key from .env
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("No GEMINI_API_KEY found in .env file!")

# Configure Google AI
genai.configure(api_key=API_KEY)

# Choose stable Gemini model
MODEL_NAME = "models/gemini-2.5-flash"
model = genai.GenerativeModel(MODEL_NAME)


# ------------------------------------------------
# SAFE GENERATE WRAPPER (prevents crashes)
# ------------------------------------------------
def safe_generate(prompt: str) -> str:
    """
    A universal safe wrapper so your server never crashes
    even if Gemini returns weird output.
    """
    try:
        response = model.generate_content(prompt)

        if not response or not response.text:
            return "I'm sorry, I couldn't process that."

        return response.text.strip()

    except Exception as e:
        print("AI Error:", e)
        return "Ugh, I'm blanking right now - give me a sec and try again?"


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

    mood = safe_generate(prompt).lower().strip()

    allowed = [
        "happy", "sad", "stressed", "angry",
        "excited", "confused", "neutral"
    ]

    for m in allowed:
        if m in mood:
            return m

    return "neutral"   # fallback


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
