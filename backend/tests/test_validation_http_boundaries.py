"""QA observer persistence only; no model, provider or application decision."""
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import helpers
from scripts.validation_ui_server import HTTPBoundaryJournal, main


def record(events):
    return {"scope": HTTPBoundaryJournal.SCOPE, "events": events}


def event(**changes):
    return {"path": "/api/check-text", "method": "POST", "status": 200,
            "content_type": "application/json", "cache_control": "no-store", **changes}


class HTTPBoundaryJournalTests(unittest.TestCase):
    def test_resume_keeps_old_two_events_and_appends_without_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "http-boundaries.json"
            previous = [event(), event(path="/api/check-url", status=422)]
            path.write_text(json.dumps(record(previous)))
            journal = HTTPBoundaryJournal(path)
            journal.append("/api/upload", "POST", 200, "application/json", "no-store")
            stored = json.loads(path.read_text())
            self.assertEqual(stored, record([*previous, event(path="/api/upload")]))
            self.assertEqual(HTTPBoundaryJournal(path).events, stored["events"])

    def test_invalid_existing_data_refused_unchanged(self):
        invalid = [[], {}, record("not-events"), {**record([]), "token": "private-marker"},
                   {**record([]), "scope": "private-marker"}, record([event(secret="private-marker")])]
        for field, value in (("path", "/api/check-text?token=private-marker"), ("path", "/api/history/private-marker"),
                             ("method", "private-marker"), ("status", True), ("status", 600),
                             ("content_type", "application/json; token=private-marker"),
                             ("cache_control", "private-marker"), ("path", []), ("method", {})):
            invalid.append(record([event(**{field: value})]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "http-boundaries.json"
            for value in invalid:
                with self.subTest(value=value):
                    content = json.dumps(value)
                    path.write_text(content)
                    with self.assertRaisesRegex(ValueError, "Invalid local HTTP boundary journal"):
                        HTTPBoundaryJournal(path)
                    self.assertEqual(path.read_text(), content)
            for content in ("{invalid", "\udcff"):
                path.write_bytes(content.encode("utf-8", errors="surrogatepass"))
                with self.assertRaises(ValueError):
                    HTTPBoundaryJournal(path)

    def test_untrusted_values_never_written_and_unknown_paths_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "http-boundaries.json"
            journal = HTTPBoundaryJournal(path)
            self.assertFalse(journal.append("/api/check-text?token=private-marker", "POST", 200))
            self.assertFalse(journal.append("/api/history/private-marker", "POST", 200))
            self.assertFalse(path.exists())
            journal.append("/api/check-text", "private-method-marker", 200,
                           "application/json; private-header-marker", "private-cache-marker")
            self.assertEqual(journal.events, [event(method="OTHER", content_type="other", cache_control="other")])
            self.assertNotIn("private-", path.read_text())

    def test_bounds_refuse_more_events_without_truncating_previous_history(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(HTTPBoundaryJournal, "MAX_EVENTS", 2):
            path = Path(directory) / "http-boundaries.json"
            journal = HTTPBoundaryJournal(path)
            for _ in range(2):
                journal.append("/api/check-text", "POST", 200)
            previous = path.read_bytes()
            self.assertFalse(journal.has_capacity())
            with self.assertRaises(ValueError):
                journal.append("/api/check-url", "POST", 200)
            self.assertEqual(path.read_bytes(), previous)
            self.assertEqual(len(HTTPBoundaryJournal(path).events), 2)
            path.write_text(json.dumps(record([event()] * 3)))
            with self.assertRaises(ValueError):
                HTTPBoundaryJournal(path)

    def test_final_slot_reserved_before_analysis_blocks_concurrent_admission(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(HTTPBoundaryJournal, "MAX_EVENTS", 2):
            path = Path(directory) / "http-boundaries.json"
            path.write_text(json.dumps(record([event()])))
            journal = HTTPBoundaryJournal(path)
            analysis = Mock()
            ticket = journal.reserve()  # First middleware reserves before awaiting analysis.
            analysis()
            with self.assertRaises(ValueError):
                journal.reserve()  # Second middleware must stop before analysis.
                analysis()
            self.assertFalse(journal.has_capacity())
            journal.append("/api/check-url", "POST", 200, reservation=ticket)
            journal.release(ticket)  # Middleware finally is safely idempotent.
            self.assertEqual(analysis.call_count, 1)
            self.assertEqual(len(json.loads(path.read_text())["events"]), 2)

    def test_cancelled_or_failed_request_can_release_unused_slot(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(HTTPBoundaryJournal, "MAX_EVENTS", 1):
            journal = HTTPBoundaryJournal(Path(directory) / "http-boundaries.json")
            ticket = journal.reserve()
            self.assertFalse(journal.has_capacity())
            journal.release(ticket)  # Middleware finally after exception/cancellation.
            self.assertTrue(journal.has_capacity())
            with self.assertRaises(ValueError):
                journal.append("/api/check-text", "POST", 200, reservation=ticket)
            self.assertFalse(journal.path.exists())

    def test_symlink_oversize_and_nonregular_file_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "http-boundaries.json"
            target = Path(directory) / "original.json"
            target.write_text(json.dumps(record([])))
            path.symlink_to(target)
            with self.assertRaises(ValueError):
                HTTPBoundaryJournal(path)
            path.unlink()
            path.mkdir()
            with self.assertRaises(ValueError):
                HTTPBoundaryJournal(path)
            path.rmdir()
            path.write_bytes(b" " * (HTTPBoundaryJournal.MAX_BYTES + 1))
            with self.assertRaises(ValueError):
                HTTPBoundaryJournal(path)

    def test_failed_atomic_replace_keeps_disk_and_memory_history_no_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "http-boundaries.json"
            path.write_text(json.dumps(record([event()])))
            journal = HTTPBoundaryJournal(path)
            previous = path.read_bytes()
            with patch("scripts.validation_ui_server.os.replace", side_effect=OSError("simulated failure")):
                with self.assertRaises(OSError):
                    journal.append("/api/check-url", "POST", 422)
            self.assertEqual(path.read_bytes(), previous)
            self.assertEqual(journal.events, [event()])
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_invalid_or_full_journal_stops_startup_before_private_env_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "http-boundaries.json"
            for value in ({"token": "private-marker"}, record([event()] * HTTPBoundaryJournal.MAX_EVENTS)):
                with self.subTest(full="events" in value):
                    path.write_text(json.dumps(value))
                    budget = Mock()
                    argv = ["validation_ui_server.py", "--env-file", "/not-read/private.env", "--record-dir", directory]
                    with patch("sys.argv", argv), \
                            patch("scripts.validation_ui_server.ValidationBudgetJournal", return_value=budget), \
                            patch("dotenv.dotenv_values") as private, redirect_stderr(io.StringIO()), \
                            self.assertRaises(SystemExit):
                        main()
                    private.assert_not_called()
                    budget.close.assert_called_once_with()
