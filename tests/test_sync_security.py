import os
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from backend import db
from backend.sync_import import SyncImportIn, sync_import


class CloudSyncAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        self.old_data_dir = db.DATA_DIR
        db.DATA_DIR = Path(self.temp_dir.name)
        db.DB_PATH = db.DATA_DIR / "test.db"
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        db.DATA_DIR = self.old_data_dir
        self.temp_dir.cleanup()

    def test_non_admin_cannot_import_or_clear_data(self):
        with self.assertRaises(HTTPException) as raised:
            sync_import(SyncImportIn(clear_existing=True), {"username": "staff", "role": "Staff"})
        self.assertEqual(raised.exception.status_code, 403)

    def test_admin_import_creates_backup_before_clear(self):
        with db.db() as conn:
            conn.execute(
                "INSERT INTO employees (name, created_at, updated_at) VALUES (?,?,?)",
                ("Existing Employee", "now", "now"),
            )
        result = sync_import(
            SyncImportIn(
                employees=[{"name": "Imported Employee"}],
                clear_existing=True,
            ),
            {"username": "Admin", "role": "Admin"},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["imported"]["employees"], 1)
        backups = list((db.DATA_DIR / "backups").glob("pre-sync-*.db"))
        self.assertEqual(len(backups), 1)
        with db.db() as conn:
            names = [r["name"] for r in conn.execute("SELECT name FROM employees").fetchall()]
        self.assertEqual(names, ["Imported Employee"])


if __name__ == "__main__":
    unittest.main()
