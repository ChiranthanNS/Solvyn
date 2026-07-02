# Solvyn 🤖💬

Solvyn is a full-stack **AI companion app** built with Flutter and FastAPI. It acts as a personal AI best friend — emotionally aware, remembers your conversations, and automatically writes your diary.

## ✨ Features

- 🔐 **Authentication** — Email/password + Google OAuth
- 💬 **AI Chat** — Powered by Google Gemini 2.5 Flash, with a warm, friend-like personality
- 📓 **Auto Diary** — At the end of each day, Solvyn auto-writes a personal diary entry from your conversations
- 🧠 **Long-term Memory** — Solvyn remembers past diary entries to maintain context across sessions
- 🌈 **Mood Detection** — Detects your emotional state and adapts its tone accordingly

## 🛠️ Tech Stack

### Frontend (Flutter)
- Flutter (Dart)
- Provider for state management
- Google Fonts & Flutter Animate for UI
- Google Sign-In

### Backend (FastAPI)
- Python + FastAPI
- SQLAlchemy + SQLite
- Google Gemini AI (`google-generativeai`)
- JWT Authentication
- Google OAuth2

## 📂 Project Structure

```
solvyn/
├── lib/                    # Flutter source
│   ├── main.dart
│   ├── screens/            # Login, Register, Home, Chat, Diary
│   ├── models/             # ChatMessage, DiaryEntry
│   ├── providers/          # AuthProvider
│   └── services/           # API, Auth, Chat, Diary services
├── backend/                # FastAPI backend
│   └── app/
│       ├── main.py         # App entrypoint
│       ├── models.py       # DB models
│       ├── schemas.py      # Pydantic schemas
│       ├── crud.py         # DB operations
│       ├── auth.py         # JWT auth
│       ├── ai.py           # Gemini AI
│       ├── database.py     # SQLite connection
│       └── routes/         # Auth routes (email + Google)
├── android/
├── ios/
├── web/
├── windows/
└── pubspec.yaml
```

## 🚀 Getting Started

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
flutter pub get
flutter run
```

> **Note:** Create a `backend/.env` file with your `GEMINI_API_KEY`.
