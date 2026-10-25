import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from alembic import command
from alembic.config import Config
from jose import jwt

from app import auth
from app import crud
from app.database import Base, get_db
from app import main
from app.main import app
from app.models import User, ConversationMessage, DiaryEntry, ConversationSummary


class DiaryApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_secret = auth.SECRET_KEY
        auth.SECRET_KEY = "diary-api-test-secret-with-32-plus-characters"
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=cls.engine,
        )
        Base.metadata.create_all(bind=cls.engine)
        db = cls.session_factory()
        cls.users = [
            User(email="first@example.test", hashed_password="test"),
            User(email="second@example.test", hashed_password="test"),
        ]
        db.add_all(cls.users)
        db.commit()
        for user in cls.users:
            db.refresh(user)
        db.close()
        cls.tokens = [
            auth.create_access_token({"user_id": user.id})
            for user in cls.users
        ]

        def override_get_db():
            session = cls.session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()
        auth.SECRET_KEY = cls.original_secret

    def setUp(self):
        self.client = TestClient(app)
        self.owner_headers = {"Authorization": f"Bearer {self.tokens[0]}"}
        self.other_headers = {"Authorization": f"Bearer {self.tokens[1]}"}
        db = self.session_factory()
        db.query(ConversationSummary).delete()
        db.query(ConversationMessage).delete()
        db.query(DiaryEntry).delete()
        db.commit()
        db.close()
        main._ai_request_times.clear()

    def test_diary_create_read_update_and_delete_persist(self):
        created = self.client.post(
            "/diary",
            json={"content": "A thought worth keeping."},
            headers=self.owner_headers,
        )
        self.assertEqual(created.status_code, 200)
        entry_id = created.json()["id"]

        loaded = self.client.get(f"/diary/{entry_id}", headers=self.owner_headers)
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["content"], "A thought worth keeping.")

        updated = self.client.patch(
            f"/diary/{entry_id}",
            json={"content": "An edited thought."},
            headers=self.owner_headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["content"], "An edited thought.")

        entries = self.client.get("/diary", headers=self.owner_headers)
        self.assertEqual([entry["id"] for entry in entries.json()], [entry_id])
        self.assertEqual(entries.json()[0]["content"], "An edited thought.")

        deleted = self.client.delete(f"/diary/{entry_id}", headers=self.owner_headers)
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get("/diary", headers=self.owner_headers).json(), [])

    def test_diary_records_are_isolated_between_users(self):
        created = self.client.post(
            "/diary",
            json={"content": "Private entry."},
            headers=self.owner_headers,
        )
        entry_id = created.json()["id"]

        self.assertEqual(self.client.get("/diary", headers=self.other_headers).json(), [])
        for response in (
            self.client.get(f"/diary/{entry_id}", headers=self.other_headers),
            self.client.patch(
                f"/diary/{entry_id}",
                json={"content": "Attempted edit."},
                headers=self.other_headers,
            ),
            self.client.delete(f"/diary/{entry_id}", headers=self.other_headers),
        ):
            self.assertEqual(response.status_code, 404)

        still_private = self.client.get(f"/diary/{entry_id}", headers=self.owner_headers)
        self.assertEqual(still_private.status_code, 200)
        self.assertEqual(still_private.json()["content"], "Private entry.")

    def test_diary_requires_auth_and_rejects_blank_content(self):
        self.assertEqual(self.client.get("/diary").status_code, 401)
        self.assertEqual(
            self.client.get("/diary", headers={"Authorization": "Bearer invalid"}).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                "/diary",
                json={"content": "  "},
                headers=self.owner_headers,
            ).status_code,
            422,
        )

    def test_signup_normalizes_email_and_login_rejects_invalid_credentials(self):
        signup = self.client.post(
            "/auth/signup",
            json={"email": "  New.User@Example.Test ", "password": "correct-horse-9"},
        )
        self.assertEqual(signup.status_code, 200)
        self.assertEqual(signup.json()["email"], "new.user@example.test")
        duplicate = self.client.post(
            "/auth/signup",
            json={"email": "new.user@example.test", "password": "another-password-9"},
        )
        self.assertEqual(duplicate.status_code, 400)

        login = self.client.post(
            "/auth/login",
            json={"email": "NEW.USER@example.test", "password": "correct-horse-9"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json()["access_token"])
        failed = self.client.post(
            "/auth/login",
            json={"email": "new.user@example.test", "password": "wrong-password"},
        )
        self.assertEqual(failed.status_code, 401)
        self.assertEqual(failed.json()["detail"], "Invalid email or password")

    def test_missing_expired_and_invalid_user_tokens_are_rejected(self):
        self.assertEqual(self.client.get("/diary").status_code, 401)
        expired = jwt.encode(
            {
                "user_id": self.users[0].id,
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            },
            auth.SECRET_KEY,
            algorithm=auth.ALGORITHM,
        )
        self.assertEqual(
            self.client.get(
                "/diary", headers={"Authorization": f"Bearer {expired}"}
            ).status_code,
            401,
        )

    def test_diary_title_mood_filter_and_original_timestamp(self):
        created = self.client.post(
            "/diary",
            json={
                "title": "  A new beginning ",
                "content": "Today was hopeful.",
                "mood": "happy",
            },
            headers=self.owner_headers,
        )
        self.assertEqual(created.status_code, 200)
        payload = created.json()
        self.assertEqual(payload["title"], "A new beginning")
        self.assertEqual(payload["mood"], "happy")
        original_created_at = payload["created_at"]

        updated = self.client.patch(
            f"/diary/{payload['id']}",
            json={"content": "Today was still hopeful.", "mood": "excited"},
            headers=self.owner_headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["created_at"], original_created_at)
        self.assertEqual(updated.json()["mood"], "excited")

        filtered = self.client.get(
            "/diary?q=hopeful&mood=excited", headers=self.owner_headers
        )
        self.assertEqual(len(filtered.json()), 1)
        self.assertEqual(
            self.client.get("/diary?mood=happy", headers=self.owner_headers).json(),
            [],
        )
        invalid = self.client.post(
            "/diary",
            json={"content": "A thought.", "mood": "diagnosed"},
            headers=self.owner_headers,
        )
        self.assertEqual(invalid.status_code, 422)

    def test_conversation_history_is_private_and_chat_failure_keeps_user_message(self):
        db = self.session_factory()
        crud.save_message(db, self.users[0].id, "user", "Private to one account.")
        db.close()
        owner_history = self.client.get("/ai/chat/history", headers=self.owner_headers)
        other_history = self.client.get("/ai/chat/history", headers=self.other_headers)
        self.assertEqual(len(owner_history.json()), 1)
        self.assertEqual(other_history.json(), [])

        with patch(
            "app.main.safe_generate",
            side_effect=main.HTTPException(status_code=503, detail="AI unavailable."),
        ):
            failed = self.client.post(
                "/ai/chat",
                json={"content": "A message that should remain saved."},
                headers=self.owner_headers,
            )
        self.assertEqual(failed.status_code, 503)
        messages = self.client.get("/ai/chat/history", headers=self.owner_headers).json()
        self.assertEqual(messages[-1]["message"], "A message that should remain saved.")

    def test_daily_chat_summary_is_stored_once_and_distinguished(self):
        yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
        timestamp = datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=12)
        db = self.session_factory()
        db.add(
            ConversationMessage(
                user_id=self.users[0].id,
                sender="user",
                message="A day worth reflecting on.",
                timestamp=timestamp,
            )
        )
        db.commit()
        db.close()

        with patch(
            "app.main.generate_diary_summary", return_value="A saved reflection."
        ), patch("app.main.safe_generate", return_value="A kind reply."):
            for text in ("Today is a new day.", "Another thought today."):
                response = self.client.post(
                    "/ai/chat",
                    json={"content": text},
                    headers=self.owner_headers,
                )
                self.assertEqual(response.status_code, 200)

        db = self.session_factory()
        summaries = (
            db.query(DiaryEntry)
            .filter(
                DiaryEntry.user_id == self.users[0].id,
                DiaryEntry.entry_type == "chat_summary",
                DiaryEntry.summary_day == yesterday,
            )
            .all()
        )
        marker_count = (
            db.query(ConversationSummary)
            .filter(ConversationSummary.user_id == self.users[0].id)
            .count()
        )
        self.assertEqual(len(summaries), 1)
        self.assertEqual(marker_count, 1)
        db.close()

    def test_validation_errors_do_not_echo_submitted_password(self):
        response = self.client.post(
            "/auth/signup",
            json={"email": "valid@example.test", "password": "short"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("short", response.text)
        self.assertEqual(response.json()["detail"], "Request input is invalid.")

    def test_google_password_accounts_cannot_use_the_placeholder_password(self):
        db = self.session_factory()
        google_user = crud.create_google_user(db, "google@example.test")
        legacy_user = User(
            email="legacy-google@example.test",
            hashed_password=auth.hash_password("google_oauth"),
        )
        db.add(legacy_user)
        db.commit()
        self.assertEqual(google_user.auth_provider, "google")
        db.close()

        for email in ("google@example.test", "legacy-google@example.test"):
            response = self.client.post(
                "/auth/login",
                json={"email": email, "password": "google_oauth"},
            )
            self.assertEqual(response.status_code, 401)

    def test_google_signin_is_hidden_and_rejected_without_configuration(self):
        from app.routes import auth_google

        with patch.object(auth_google, "GOOGLE_CLIENT_ID", ""):
            self.assertIsNone(self.client.get("/auth/google/config").json()["client_id"])
            response = self.client.post("/auth/google", json={"id_token": "not-a-token"})
        self.assertEqual(response.status_code, 503)

    def test_ai_reflection_checks_ownership_and_missing_provider_is_clear(self):
        created = self.client.post(
            "/diary",
            json={"content": "A small but meaningful day."},
            headers=self.owner_headers,
        )
        entry_id = created.json()["id"]
        with patch("app.main.summarize_text", return_value="A short reflection."):
            reflected = self.client.post(
                f"/diary/{entry_id}/summary", headers=self.owner_headers
            )
            forbidden = self.client.post(
                f"/diary/{entry_id}/summary", headers=self.other_headers
            )
        self.assertEqual(reflected.status_code, 200)
        self.assertEqual(reflected.json()["summary"], "A short reflection.")
        self.assertEqual(forbidden.status_code, 404)

        with patch("app.ai.model", None):
            unavailable = self.client.post(
                "/ai/summary",
                json={"text": "Please summarize this."},
                headers=self.owner_headers,
            )
        self.assertEqual(unavailable.status_code, 503)
        self.assertIn("GEMINI_API_KEY", unavailable.json()["detail"])

    def test_ai_rate_limit_and_provider_timeout_errors(self):
        with patch("app.main.detect_mood", return_value="happy"):
            for _ in range(8):
                response = self.client.post(
                    "/ai/mood",
                    json={"text": "I feel good."},
                    headers=self.owner_headers,
                )
                self.assertEqual(response.status_code, 200)
            limited = self.client.post(
                "/ai/mood",
                json={"text": "One more."},
                headers=self.owner_headers,
            )
        self.assertEqual(limited.status_code, 429)
        self.assertIn("Retry-After", limited.headers)

        class TimeoutModel:
            def generate_content(self, *_args, **_kwargs):
                raise TimeoutError("provider-internal-detail")

        main._ai_request_times.clear()
        with patch("app.ai.model", TimeoutModel()):
            timed_out = self.client.post(
                "/ai/summary",
                json={"text": "A request that times out."},
                headers=self.owner_headers,
            )
        self.assertEqual(timed_out.status_code, 502)
        self.assertEqual(timed_out.json()["detail"], "The AI provider request failed.")
        self.assertNotIn("provider-internal-detail", timed_out.text)

    def test_session_secret_must_be_strong_enough_to_issue_tokens(self):
        db = self.session_factory()
        db.add(
            User(
                email="secret-test@example.test",
                hashed_password=auth.hash_password("valid-password-42"),
            )
        )
        db.commit()
        db.close()
        original = auth.SECRET_KEY
        auth.SECRET_KEY = "too-short"
        try:
            response = self.client.post(
                "/auth/login",
                json={
                    "email": "secret-test@example.test",
                    "password": "valid-password-42",
                },
            )
        finally:
            auth.SECRET_KEY = original
        self.assertEqual(response.status_code, 503)
        self.assertIn("SESSION_SECRET", response.json()["detail"])

    def test_migration_preserves_existing_sqlite_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "legacy.sqlite")
            legacy_engine = create_engine(f"sqlite:///{db_path}")
            with legacy_engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR UNIQUE NOT NULL, hashed_password VARCHAR NOT NULL)"
                )
                connection.exec_driver_sql(
                    "CREATE TABLE diary_entries (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), content TEXT NOT NULL, created_at DATETIME)"
                )
                connection.exec_driver_sql(
                    "CREATE TABLE conversation_messages (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), sender VARCHAR NOT NULL, message TEXT NOT NULL, timestamp DATETIME)"
                )
                connection.exec_driver_sql(
                    "INSERT INTO users (id, email, hashed_password) VALUES (77, 'legacy@example.test', 'existing-hash')"
                )
                connection.exec_driver_sql(
                    "INSERT INTO diary_entries (id, user_id, content, created_at) VALUES (91, 77, 'Keep this entry.', '2025-01-02 03:04:05')"
                )
                connection.exec_driver_sql(
                    "INSERT INTO conversation_messages (id, user_id, sender, message, timestamp) VALUES (101, 77, 'user', 'Keep this conversation.', '2025-01-02 03:05:05')"
                )

            config = Config(os.path.join("backend", "alembic.ini"))
            config.attributes["database_url"] = f"sqlite:///{db_path}"
            with legacy_engine.connect() as connection:
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
            with legacy_engine.connect() as connection:
                user = connection.exec_driver_sql(
                    "SELECT email, hashed_password, auth_provider FROM users WHERE id=77"
                ).one()
                entry = connection.exec_driver_sql(
                    "SELECT content, title, mood, entry_type, created_at, updated_at FROM diary_entries WHERE id=91"
                ).one()
                message = connection.exec_driver_sql(
                    "SELECT message FROM conversation_messages WHERE id=101"
                ).one()
                self.assertEqual(
                    tuple(user),
                    ("legacy@example.test", "existing-hash", "password"),
                )
                self.assertEqual(entry[0], "Keep this entry.")
                self.assertEqual(entry[3], "user")
                self.assertEqual(entry[4], entry[5])
                self.assertEqual(message[0], "Keep this conversation.")
            legacy_engine.dispose()

    def test_migration_initializes_a_fresh_database(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "fresh.sqlite")
            fresh_engine = create_engine(f"sqlite:///{db_path}")
            config = Config(os.path.join("backend", "alembic.ini"))
            config.attributes["database_url"] = f"sqlite:///{db_path}"
            with fresh_engine.connect() as connection:
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
            with fresh_engine.connect() as connection:
                tables = set(
                    connection.exec_driver_sql(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).scalars()
                )
            self.assertTrue(
                {"users", "diary_entries", "conversation_messages", "conversation_summaries"}
                .issubset(tables)
            )
            fresh_engine.dispose()


if __name__ == "__main__":
    unittest.main()
