# Running Solvyn on Replit

- The primary Replit app is the browser client in `web/`, served by FastAPI from `backend/app/main.py`.
- Run it on port 5000 with:
  `PYTHONPATH=backend .pythonlibs/bin/python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 5000`
- `SESSION_SECRET` is required for registration and sign-in; configure at least 32 random characters and keep it in Replit Secrets.
- `GEMINI_API_KEY` is optional for startup and diary CRUD, but required for AI chat and AI-powered reflection.
- Run development schema updates explicitly with:
  `PYTHONPATH=backend .pythonlibs/bin/python -m alembic -c backend/alembic.ini upgrade head`
- The app workflow does not perform database DDL. Replit-managed production schema changes go through Publish; never run the development Alembic command against production.
- Replit provides a managed PostgreSQL database in this workspace. It was empty before this setup, and only its development schema was migrated. Its production persistence/recovery has not been exercised.
- If `DATABASE_URL` is absent, the app uses `solvyn.db` in the project root. SQLite files may not survive deployment replacement; verify durable storage and backups before relying on them for real records.
- Configure `GOOGLE_CLIENT_ID` to enable browser Google sign-in; without it, email/password authentication remains available.
- Root `lib/`, `android/`, and `ios/` contain the retained Flutter client. `frontend/` is a separate older Flutter implementation and is not used by the Replit workflow.
- Install dependencies with `python -m pip install -r backend/requirements.txt`, then run the command above from the repository root.
