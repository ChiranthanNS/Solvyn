# Solvyn

Solvyn is a private diary and AI reflection companion. Users can create, revisit, edit, and delete their own journal entries, and have thoughtful conversations with an AI companion when Gemini is configured.

## What is implemented

- Email/password registration and sign-in with signed, expiring JWTs
- Per-user diary entries with create, list, open, edit, and delete operations
- Confirmation before permanent diary deletion in the browser and root Flutter client
- Conversation history stored and retrieved per authenticated user
- Gemini-backed chat and reflection endpoints; requests fail clearly if the provider is unavailable
- Responsive browser client served by FastAPI
- Root Flutter client retained for Android/iOS

Browser Google sign-in, password recovery, diary titles and mood fields, and managed database migrations are not implemented.

## Replit

The `Start application` workflow runs the FastAPI application on port 5000. FastAPI serves the browser client from `web/`.

Required configuration:

- `SESSION_SECRET` — signs authentication tokens. A secret is available in this workspace.
- `GEMINI_API_KEY` — required for AI chat and AI-powered reflection endpoints. Add it with Replit Secrets to enable these features. Diary and account features work without it.

Optional configuration includes `GEMINI_MODEL`, `DATABASE_URL`, `CORS_ORIGINS`, and `GOOGLE_CLIENT_ID`; see `backend/.env.example`.

## Run locally

From the repository root:

```bash
python -m pip install -r backend/requirements.txt
export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export GEMINI_API_KEY="your-key" # optional; enables AI features
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 5000
```

Open `http://localhost:5000`. For local configuration, copy `backend/.env.example` to `backend/.env` and set the values there.

## Flutter client

The root `lib/`, `android/`, and `ios/` directories are the retained mobile client and platform configuration. It uses the same FastAPI contracts as the browser app.

```bash
flutter pub get
flutter run
```

Android emulators use `http://10.0.2.2:5000` by default. To use another API host, pass `--dart-define=SOLVYN_API_URL=https://your-api.example`.

The separate `frontend/` directory is an older Flutter implementation with its own package and platform files. It is not referenced by the Replit workflow and is retained for reference; it has not been consolidated into the root mobile client.

## Tests

Run backend regression tests from the repository root:

```bash
PYTHONPATH=backend python -m unittest discover -s backend/tests
```

The Flutter widget tests are under `test/` (root mobile client) and `frontend/test/` (retained older client); Flutter SDK availability is required to run them.

## Data and deployment notes

The default database is SQLite at `./solvyn.db`, preserving the imported storage behavior. The file is ignored by Git, but SQLite data may not be durable across deployment replacement unless the database file is stored in a durable location and backed up. Do not rely on this default for important production diary records without addressing storage durability.

The schema is initialized with SQLAlchemy `create_all`; there is no migration framework. The diary CRUD additions do not alter the database schema. AI provider quota and rate limiting should be addressed before public launch.

The `/ai/solve` API is retained for compatibility but is no longer part of the primary diary and reflection browser experience.
