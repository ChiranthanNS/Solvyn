import os
import unittest

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth
from app.database import Base, get_db
from app.main import app
from app.models import User


class DiaryApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_secret = auth.SECRET_KEY
        auth.SECRET_KEY = "diary-api-test-secret"
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


if __name__ == "__main__":
    unittest.main()
