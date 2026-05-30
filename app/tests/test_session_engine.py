import json
import os
import tempfile
import unittest

from app.core.session_engine import SessionEngine
from app.data.storage import Storage


class SessionEngineTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(self.temp_dir.name, "study_data.json")
        self.storage = Storage(path=self.storage_path)
        self.engine = SessionEngine(self.storage)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pause_and_resume_active_session(self):
        session = self.engine.start_focus(subject="Math", minutes=1, task="Review")
        self.assertEqual(session["state"], "running")

        paused = self.engine.pause()
        self.assertEqual(paused["state"], "paused")
        self.assertEqual(self.storage.profile["active_session"]["state"], "paused")

        resumed = self.engine.resume()
        self.assertEqual(resumed["state"], "running")
        self.assertEqual(self.storage.profile["active_session"]["state"], "running")

    def test_complete_focus_records_session_and_updates_task(self):
        task = {
            "id": 1,
            "title": "Read chapter",
            "subject": "History",
            "due_date": "",
            "tags": [],
            "details": "",
            "status": "open",
            "minutes_logged": 0,
        }
        self.storage.profile.setdefault("tasks", []).append(task)
        active = self.engine.start_focus(
            subject="History",
            minutes=1,
            task="Read chapter",
            task_id=1,
        )

        # Advance time at least one tick to update the session
        self.engine.tick()
        self.engine.complete_focus(active)

        self.assertIsNone(self.storage.profile.get("active_session"))
        self.assertEqual(len(self.storage.profile.get("sessions", [])), 1)
        recorded = self.storage.profile["sessions"][0]
        self.assertEqual(recorded["subject"], "History")
        self.assertEqual(recorded["task_title"], "Read chapter")
        self.assertGreaterEqual(recorded["studied_minutes"], 0)

        updated_task = next(t for t in self.storage.profile["tasks"] if t["id"] == 1)
        self.assertGreaterEqual(updated_task["minutes_logged"], 0)

    def test_complete_focus_with_no_active_session_returns_none(self):
        result = self.engine.complete_focus(None)
        self.assertIsNone(result)
        self.assertIsNone(self.storage.profile.get("active_session"))


if __name__ == "__main__":
    unittest.main()
