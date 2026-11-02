import os
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from backend import db


class FreshWebAccountTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_path = db.DB_PATH
        db.DB_PATH = Path(self.temp_dir.name) / "test.db"
        os.environ["WEB_SESSION_SECRET"] = "test-session-secret-that-is-at-least-32-characters"
        os.environ.pop("WEB_BOOTSTRAP_USERS", None)
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.original_path
        self.temp_dir.cleanup()
        os.environ.pop("WEB_SESSION_SECRET", None)

    def create_admin(self, username="test-admin", password="Initial-Password-123"):
        from backend.main import FirstAdminSetupIn, first_admin_setup
        result = first_admin_setup(FirstAdminSetupIn(
            username=username, display_name="Test Administrator", password=password
        ))
        return result

    def test_fresh_database_has_no_default_or_migrated_users(self):
        with db.db() as conn:
            count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        self.assertEqual(count, 0)

    def test_first_admin_setup_creates_account_and_rejects_second_setup(self):
        from backend.main import FirstAdminSetupIn, first_admin_setup
        from backend import auth
        result = self.create_admin()
        self.assertTrue(result["ok"])
        self.assertIsNotNone(auth.authenticate("test-admin", "Initial-Password-123"))
        with self.assertRaises(HTTPException) as raised:
            first_admin_setup(FirstAdminSetupIn(
                username="another-admin", display_name="Second", password="Another-Password-123"
            ))
        self.assertEqual(raised.exception.status_code, 409)

    def test_first_admin_setup_rejects_short_password(self):
        from backend.main import FirstAdminSetupIn
        with self.assertRaises(Exception):
            FirstAdminSetupIn(username="admin-user", display_name="Admin", password="short")

    def test_password_change_updates_hash_and_invalidates_old_sessions(self):
        from backend import auth
        from backend.main import PasswordChangeIn, change_password
        self.create_admin()
        user = auth.authenticate("test-admin", "Initial-Password-123")
        old_token = auth.create_session(int(user["id"]))
        result = change_password(
            PasswordChangeIn(current_password="Initial-Password-123", new_password="Replacement-Password-456"),
            user,
        )
        self.assertTrue(result["ok"])
        self.assertIsNone(auth.session_user(old_token))
        self.assertIsNotNone(auth.session_user(result["token"]))
        self.assertIsNone(auth.authenticate("test-admin", "Initial-Password-123"))
        self.assertIsNotNone(auth.authenticate("test-admin", "Replacement-Password-456"))

    def test_password_change_rejects_wrong_current_password(self):
        from backend import auth
        from backend.main import PasswordChangeIn, change_password
        self.create_admin()
        user = auth.authenticate("test-admin", "Initial-Password-123")
        with self.assertRaises(HTTPException):
            change_password(
                PasswordChangeIn(current_password="incorrect-password", new_password="Replacement-Password-456"),
                user,
            )

    def test_session_survives_database_session_table_cleanup(self):
        from backend import auth
        self.create_admin()
        user = auth.authenticate("test-admin", "Initial-Password-123")
        token = auth.create_session(int(user["id"]))
        with db.db() as conn:
            conn.execute("DELETE FROM sessions")
        self.assertIsNotNone(auth.session_user(token))

    def test_restart_does_not_change_new_web_account_password(self):
        from backend import auth
        self.create_admin()
        user = auth.authenticate("test-admin", "Initial-Password-123")
        token = auth.create_session(int(user["id"]))
        db.init_db()
        self.assertIsNotNone(auth.session_user(token))
        self.assertIsNotNone(auth.authenticate("test-admin", "Initial-Password-123"))

    def test_password_hash_verification(self):
        hashed = db.hash_password("a-unique-long-password")
        self.assertTrue(db.verify_password("a-unique-long-password", hashed))
        self.assertFalse(db.verify_password("wrong-password", hashed))


if __name__ == "__main__":
    unittest.main()
