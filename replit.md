# Running Solvyn on Replit

- The primary Replit app is the browser client in `web/`, served by FastAPI from `backend/app/main.py`.
- Run it on port 5000 with:
  `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 5000`
- `SESSION_SECRET` is required for registration and sign-in. Keep it in Replit Secrets.
- `GEMINI_API_KEY` is optional for startup and diary CRUD, but required for AI chat and AI-powered reflection.
- Keep the existing SQLite database behavior unless a deliberate, data-safe storage migration is requested.
- Root `lib/`, `android/`, and `ios/` contain the retained Flutter client. `frontend/` is a separate older Flutter implementation and is not used by the Replit workflow.
- Start locally with `python -m pip install -r backend/requirements.txt`, then run the command above from the repository root.
