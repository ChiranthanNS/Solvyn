# Solvyn

Solvyn is a private diary and AI reflection companion. Users can create, revisit, edit, and delete their own journal entries, and have thoughtful conversations with an AI companion when Gemini is configured.

## What is implemented

- Email/password registration and sign-in with signed, expiring JWTs
- Per-user diary entries with create, list, open, edit, and delete operations
- Optional diary titles and validated moods, with title/content search and mood/date filters in the browser
- Confirmation before permanent diary deletion in the browser and root Flutter client
- Conversation history stored and retrieved per authenticated user
- Gemini-backed chat and optional entry reflections; AI-generated daily chat summaries are marked separately and protected by database-backed idempotency
- Alembic migration for existing SQLite or SQLAlchemy-compatible databases, with a data-preserving upgrade
- Responsive browser client served by FastAPI
- Root Flutter client retained for Android/iOS

Password recovery is not implemented because no email-delivery and verification service is configured. Browser Google sign-in is enabled only when `GOOGLE_CLIENT_ID` is configured. No managed database or durable production storage has been configured.

## Replit

The `Start application` workflow runs FastAPI on port 5000. FastAPI serves the browser client from `web/`. The workflow does not run DDL; apply development migrations explicitly before starting a fresh database.

Required configuration:

- `SESSION_SECRET` — signs authentication tokens; use at least 32 random characters. A workspace secret is already available.
- `GEMINI_API_KEY` — required for AI chat and AI-powered reflection endpoints. Add it with Replit Secrets to enable these features. Diary and account features work without it.

Optional configuration includes `GEMINI_MODEL`, `DATABASE_URL`, `CORS_ORIGINS`, and `GOOGLE_CLIENT_ID`; see `backend/.env.example`. Google sign-in requires a web OAuth client ID authorized for the app's origin. No fake sign-in button is shown when that configuration is missing.

## Run locally

From the repository root:

```bash
python -m pip install -r backend/requirements.txt
export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export GEMINI_API_KEY="your-key" # optional; enables AI features
PYTHONPATH=backend python -m alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 5000
```

Open `http://localhost:5000`. For local configuration, copy `backend/.env.example` to `backend/.env` and set the values there.

## Flutter client

The root `lib/`, `android/`, and `ios/` directories are the retained mobile client and platform configuration. It uses the same FastAPI contracts as the browser app.

```bash
flutter pub get
flutter run
```

Android emulators use `http://10.0.2.2:5000` by default. To use another API host, pass `--dart-define=SOLVYN_API_URL=https://your-api.example`. Google sign-in needs the OAuth client ID at build time with `--dart-define=GOOGLE_CLIENT_ID=...`.

The separate `frontend/` directory is an older Flutter implementation with its own package and platform files. It is not referenced by the Replit workflow and is retained for reference; it has not been consolidated into the root mobile client.

## Tests

Run backend regression tests from the repository root:

```bash
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
```

The Flutter widget tests are under `test/` (root mobile client) and `frontend/test/` (retained older client); Flutter SDK availability is required to run them.

## Data and deployment notes

The default database is SQLite at the absolute project-root path `solvyn.db`. `DATABASE_URL` can select another supported SQLAlchemy database. The default file is ignored by Git and is not guaranteed to survive deployment replacement; do not rely on it for important production records until durable storage and recovery have been verified.

The app uses Alembic. Apply `upgrade head` explicitly to the development database when initializing or changing its schema. The app and workflow do not perform startup-time DDL. Replit-managed production schema changes are applied through Replit's Publish flow; do not point an app-startup migration command at production. The current Replit development PostgreSQL database had no tables before setup; the migration was applied only to that empty development database. No production database or private records were changed.

Replit's managed PostgreSQL has scheduled backups and point-in-time recovery; availability and retention depend on the account's current plan. Use the database recovery controls before/after a production schema release and test recovery separately. Replit development DB history is available through workspace checkpoints. For an external PostgreSQL database, use its own supported backup/restore tools and test a restore to an isolated database before relying on it. The forward-only Alembic migration should be rolled back by restoring a verified backup, not by dropping user data.

For local SQLite databases, create a consistent backup from the repository root while the app is running:

```bash
python - <<'PY'
import sqlite3
source = sqlite3.connect("solvyn.db")
backup = sqlite3.connect("solvyn.backup.sqlite")
source.backup(backup)
backup.close()
source.close()
PY
```

Verify the backup by opening it and checking the `users`, `diary_entries`, and `conversation_messages` tables before relying on it. To restore, stop the app, preserve the current database file, then copy the verified backup into place. Keep backups outside Git and the deployment bundle. This procedure does not provide a scheduled or off-site backup.

The API limits AI operations to eight requests per user per minute in each application process; this is a basic in-memory guard, not a distributed production rate limiter. Missing Gemini configuration leaves diary and account operations usable. Chat messages are stored before AI generation, and a failed provider request can therefore leave the user's message in history.

Browser bearer tokens remain in `sessionStorage` and are cleared on sign-out or expiry. The API uses explicit origins and does not use cookie authentication. Request validation responses omit submitted values. Google ID tokens are verified by the backend and only verified Google emails can authenticate.

Current limitations: no verified email service/password recovery, no committed browser end-to-end test runner, production database recovery has not been exercised, and no release deployment verification. Flutter was not compiled in this environment because the Flutter SDK is unavailable.

The `/ai/solve` API is retained for compatibility but is no longer part of the primary diary and reflection browser experience.
