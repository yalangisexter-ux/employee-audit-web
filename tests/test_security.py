import os
import tempfile
import unittest
from pathlib import Path

from backend import db


class SecurityBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_path = db.DB_PATH
        db.DB_PATH = Path(self.temp_dir.name) / "test.db"
        os.environ.pop("WEB_ADMIN_USERNAME", None)
        os.environ.pop("WEB_ADMIN_PASSWORD", None)
        os.environ.pop("WEB_DEVELOPER_USERNAME", None)
        os.environ.pop("WEB_DEVELOPER_PASSWORD", None)

    def tearDown(self):
        db.DB_PATH = self.original_path
        self.temp_dir.cleanup()
        os.environ.pop("WEB_BOOTSTRAP_USERS", None)

    def test_no_default_users_are_created(self):
        os.environ["WEB_BOOTSTRAP_USERS"] = "false"
        db.init_db()
        with db.db() as conn:
            count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        self.assertEqual(count, 0)

    def test_bootstrap_requires_secret_credentials(self):
        os.environ["WEB_BOOTSTRAP_USERS"] = "true"
        with self.assertRaises(RuntimeError):
            db.init_db()


    def test_password_change_updates_hash_and_invalidates_old_sessions(self):
        from backend import auth
        from backend.main import PasswordChangeIn, change_password

        os.environ["WEB_BOOTSTRAP_USERS"] = "true"
        os.environ["WEB_ADMIN_USERNAME"] = "test-admin"
        os.environ["WEB_ADMIN_PASSWORD"] = "Initial-Password-123"
        db.init_db()
        user = auth.authenticate("test-admin", "Initial-Password-123")
        self.assertIsNotNone(user)
        old_token = auth.create_session(int(user["id"]))

        result = change_password(
            PasswordChangeIn(
                current_password="Initial-Password-123",
                new_password="Replacement-Password-456",
            ),
            user,
        )
        self.assertTrue(result["ok"])
        self.assertNotEqual(old_token, result["token"])
        self.assertIsNone(auth.session_user(old_token))
        self.assertIsNotNone(auth.session_user(result["token"]))
        self.assertIsNone(auth.authenticate("test-admin", "Initial-Password-123"))
        self.assertIsNotNone(auth.authenticate("test-admin", "Replacement-Password-456"))

    def test_password_change_rejects_wrong_current_password(self):
        from fastapi import HTTPException
        from backend import auth
        from backend.main import PasswordChangeIn, change_password

        os.environ["WEB_BOOTSTRAP_USERS"] = "true"
        os.environ["WEB_ADMIN_USERNAME"] = "test-admin"
        os.environ["WEB_ADMIN_PASSWORD"] = "Initial-Password-123"
        db.init_db()
        user = auth.authenticate("test-admin", "Initial-Password-123")
        with self.assertRaises(HTTPException):
            change_password(
                PasswordChangeIn(
                    current_password="incorrect-password",
                    new_password="Replacement-Password-456",
                ),
                user,
            )

    def test_password_hash_verification(self):
        hashed = db.hash_password("a-unique-long-password")
        self.assertTrue(db.verify_password("a-unique-long-password", hashed))
        self.assertFalse(db.verify_password("wrong-password", hashed))


if __name__ == "__main__":
    unittest.main()
