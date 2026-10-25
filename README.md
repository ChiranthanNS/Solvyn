# Solvyn

Solvyn is a problem-solving workspace with a responsive browser interface and a FastAPI backend. It accepts a problem, requests a structured analysis from Gemini, and shows the returned steps, solution tree, code or formula, and provider-reported metrics. Account history and diary entries are stored per user.

## Current features

- Email/password registration and sign-in with JWT authentication
- Authenticated problem solving through Gemini
- Structured analysis, steps, solution tree, optional code and formula, and response metrics
- Saved conversation history and personal diary entries
- Responsive browser interface served by the FastAPI application
- Existing Flutter client retained under `lib/`, plus the original Android and iOS projects

Projects, connected tools, browser Google sign-in, and shared/team workspaces are not implemented in the current backend.

## Run on Replit

The Replit workflow runs the FastAPI server on port 5000 and serves the browser app from `web/`.

Required secrets:

- `SESSION_SECRET` — used to sign authentication tokens
- `GEMINI_API_KEY` — required for AI chat and problem-solving requests

`SESSION_SECRET` is already available in this workspace. Add `GEMINI_API_KEY` through Replit Secrets before using AI features. Without the Gemini key, the app still starts and clearly reports that AI is unavailable.

## Run locally

From the repository root:

```bash
python -m pip install -r backend/requirements.txt
export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export GEMINI_API_KEY="your-key"
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 5000
```

Open `http://localhost:5000`. For local configuration, copy `backend/.env.example` to `backend/.env` and set the values there instead of exporting them.

## Configuration

| Variable | Purpose |
| --- | --- |
| `SESSION_SECRET` | JWT signing key; do not use a checked-in or hardcoded value |
| `GEMINI_API_KEY` | Enables AI solve and chat endpoints |
| `GEMINI_MODEL` | Gemini model name; defaults to `gemini-2.5-flash` |
| `DATABASE_URL` | SQLAlchemy connection string; defaults to the existing local SQLite database |
| `CORS_ORIGINS` | Optional comma-separated origins for a separately hosted client |

The browser client uses the same origin as the API by default. The retained Flutter client can be pointed at an API host with `--dart-define=SOLVYN_API_URL=https://your-api.example`; Android emulators may need `http://10.0.2.2:5000`.

## Important deployment notes

The default database remains SQLite to preserve the imported project’s storage behavior. Before relying on production data, use a durable database/file location and a deliberate backup strategy. The current schema is initialized with SQLAlchemy `create_all`; schema changes are not yet managed through migrations. AI provider usage also needs an operational quota/rate-limit policy before public launch.

The root Flutter client and `frontend/` are retained from the imported repository. The responsive browser workspace in `web/` is the interface used by the Replit workflow.
