"""QA-only persistent paid admission, without credentials or real providers."""
from contextlib import contextmanager, redirect_stderr
import asyncio
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

import helpers
import httpx
from app.services.hive_service import HiveV3Budget, HIVE_V3_API_URL
from app.core.serper_client import NewsSearch
from app.services.public_fetch import FetchedResource
from scripts.validation_ui_server import (
    CAPS, HIVE_QA_CAPS, KEYS, ValidationBudgetJournal,
    DIAGNOSTIC_TEXT_CONTROLS, PublicSourceDiagnostics, diagnostic_source_url,
    diagnostic_document, install_source_diagnostics,
    build_parser, request_provider, validate_arguments,
)


@contextmanager
def journal(path, **caps):
    value = ValidationBudgetJournal(path, {**CAPS, **caps})
    try:
        yield value
    finally:
        value.close()


class QAArgumentTests(unittest.TestCase):
    def parse(self, *args):
        parser = build_parser()
        value = parser.parse_args(["--env-file", "/not-read/private.env", "--record-dir", "/not-written", *args])
        return value, validate_arguments(parser, value)

    def test_paid_provider_needs_both_approvals_before_any_private_file(self):
        for arguments in (
            ("--providers", "hive"),
            ("--providers", "hive", "--free-credits-confirmed"),
            ("--providers", "hive", "--hive-paid-budget-approved"),
            ("--hive-paid-budget-approved", "--free-credits-confirmed"),
        ):
            with self.subTest(arguments=arguments), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.parse(*arguments)

    def test_explicit_hive_keys_only_from_narrow_allowlist(self):
        arguments, (selected, caps) = self.parse("--providers", "hive", "--free-credits-confirmed", "--hive-paid-budget-approved")
        self.assertEqual(selected, {"hive"})
        self.assertTrue(arguments.hive_paid_budget_approved)
        self.assertEqual(KEYS["hive"], ("HIVE_V3_API_KEY", "HIVE_API_KEY"))
        self.assertEqual(caps["hive"], 3)
        self.assertEqual(HIVE_QA_CAPS, {"image_requests": 2, "audio_seconds": 5, "audio_jobs": 1})

    def test_gemini_comparison_default_and_explicit_openrouter_profile(self):
        default, _ = self.parse()
        explicit, _ = self.parse("--comparison-provider", "openrouter")
        self.assertEqual(default.comparison_provider, "gemini")
        self.assertEqual(explicit.comparison_provider, "openrouter")

    def test_public_and_free_detector_caps_are_bounded_without_raising_other_caps(self):
        _, (_, caps) = self.parse("--providers", "public_fetch,sightengine", "--free-credits-confirmed",
                                 "--public-fetch-cap", "40", "--sightengine-request-cap", "6")
        self.assertEqual(caps["public_fetch"], 40)
        self.assertEqual(caps["sightengine"], 6)
        self.assertEqual(caps["news"], 22)
        self.assertEqual(caps["openrouter"], 9)
        self.assertEqual(caps["gemini"], 12)
        for arguments in (("--public-fetch-cap", "41"), ("--sightengine-request-cap", "7"), ("--gemini-request-cap", "13")):
            with self.subTest(arguments=arguments), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.parse(*arguments)

    def test_hive_only_fixed_v3_post_allowed(self):
        self.assertEqual(request_provider(httpx.Request("POST", HIVE_V3_API_URL)), "hive")
        for method, url in (
            ("GET", HIVE_V3_API_URL), ("POST", HIVE_V3_API_URL + "?api_key=not-for-output"),
            ("POST", "http://api.thehive.ai/api/v3/model"),
            ("POST", "https://api.thehive.ai/api/v2/task/sync"),
            ("POST", "https://api.thehive.ai.evil.test/api/v3/model"),
        ):
            self.assertIsNone(request_provider(httpx.Request(method, url)))


class PersistentQABudgetTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"HIVE_V3_IMAGE_REQUEST_LIMIT": "2", "HIVE_V3_AUDIO_SECONDS_LIMIT": "5"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_two_image_and_one_five_second_reservations_persist_before_send(self):
        with tempfile.TemporaryDirectory() as directory, journal(Path(directory) / "journal.json") as value:
            original = HiveV3Budget().reserve
            for _ in range(2):
                self.assertIsNone(value.reserve_hive(original, "image"))
                record = json.loads(value.path.read_text())
                self.assertEqual(record["hive_reservations"]["image_requests"], value.hive["image_requests"])
                self.assertEqual(record["counts"].get("hive", 0), value.counts["hive"])
                value.reserve_send("hive", "POST")
            self.assertIsNone(value.reserve_hive(original, "audio", 5))
            value.reserve_send("hive", "POST")
            self.assertEqual(value.hive, HIVE_QA_CAPS)
            record = json.loads(value.path.read_text())
            self.assertEqual(record["counts"]["hive"], 3)
            self.assertEqual(record["events"][-1]["transport_status"], "reserved")
            self.assertEqual(value.reserve_hive(original, "image")["status"], "budget_exhausted")
            self.assertEqual(value.reserve_hive(original, "audio", .1)["status"], "budget_exhausted")

    def test_rounding_above_five_seconds_blocks_without_production_reservation(self):
        with tempfile.TemporaryDirectory() as directory, journal(Path(directory) / "journal.json") as value:
            original = Mock(wraps=HiveV3Budget().reserve)
            self.assertEqual(value.reserve_hive(original, "audio", 5.001)["status"], "budget_exhausted")
            original.assert_not_called()
            self.assertEqual(value.hive["audio_jobs"], 0)
            self.assertIsNone(value.reserve_hive(original, "audio", 4.001))
            self.assertEqual(value.hive["audio_seconds"], 5)

    def test_short_first_audio_cannot_create_second_audio_job(self):
        with tempfile.TemporaryDirectory() as directory, journal(Path(directory) / "journal.json") as value:
            original = HiveV3Budget().reserve
            self.assertIsNone(value.reserve_hive(original, "audio", 1))
            self.assertEqual(value.reserve_hive(original, "audio", 1)["status"], "budget_exhausted")
            self.assertEqual(value.hive["audio_seconds"], 1)
            self.assertEqual(value.hive["audio_jobs"], 1)

    def test_restart_preserves_reservations_and_send_counts_including_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.json"
            with journal(path) as first:
                self.assertIsNone(first.reserve_hive(HiveV3Budget().reserve, "image"))
                event = first.reserve_send("hive", "POST")
                event["transport_status"] = "incomplete"
                first.persist()
            with journal(path) as resumed:
                self.assertEqual(resumed.hive["image_requests"], 1)
                self.assertEqual(resumed.counts["hive"], 1)
                original = HiveV3Budget().reserve  # Process reset cannot reset persisted admission.
                self.assertIsNone(resumed.reserve_hive(original, "image"))
                resumed.reserve_send("hive", "POST")
                self.assertEqual(resumed.reserve_hive(original, "image")["status"], "budget_exhausted")
                self.assertEqual(resumed.events[0]["transport_status"], "incomplete")

    def test_unconsumed_reservation_survives_restart_but_cannot_be_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.json"
            with journal(path) as first:
                self.assertIsNone(first.reserve_hive(HiveV3Budget().reserve, "image"))
            with journal(path) as resumed:
                with self.assertRaises(ValueError):
                    resumed.reserve_send("hive", "POST")
                self.assertEqual(resumed.counts["hive"], 0)
                self.assertEqual(resumed.hive["image_requests"], 1)

    def test_original_budget_is_not_weakened_or_refunded(self):
        with tempfile.TemporaryDirectory() as directory, journal(Path(directory) / "journal.json") as value:
            with patch.dict(os.environ, {"HIVE_V3_IMAGE_REQUEST_LIMIT": "0"}):
                self.assertEqual(value.reserve_hive(HiveV3Budget().reserve, "image")["status"], "disabled")
            self.assertEqual(value.hive["image_requests"], 0)
            for duration in (None, True, float("nan"), float("inf"), 0, -1, 121):
                with self.subTest(duration=duration):
                    self.assertEqual(value.reserve_hive(HiveV3Budget().reserve, "audio", duration)["status"], "invalid_configuration")
            self.assertEqual(value.hive["audio_jobs"], 0)

    def test_failed_persistence_never_issues_paid_send_permit(self):
        with tempfile.TemporaryDirectory() as directory, journal(Path(directory) / "journal.json") as value:
            with patch.object(value, "persist", side_effect=OSError("private-path-marker")):
                with self.assertRaises(OSError):
                    value.reserve_hive(HiveV3Budget().reserve, "image")
            with self.assertRaises(ValueError):
                value.reserve_send("hive", "POST")
            self.assertEqual(value.counts["hive"], 0)

    def test_generic_send_count_persists_before_response_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.json"
            with journal(path, public_fetch=1) as first:
                first.reserve_send("public_fetch", "GET")
                self.assertEqual(json.loads(path.read_text())["counts"]["public_fetch"], 1)
            with journal(path, public_fetch=1) as resumed:
                with self.assertRaises(ValueError):
                    resumed.reserve_send("public_fetch", "GET")

    def test_asr_creation_ceiling_survives_restart_without_new_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.json"
            with journal(path) as first:
                first.reserve_send("assemblyai", "POST", asr_category="upload")
                first.reserve_send("assemblyai", "POST", asr_category="job")
            with journal(path) as resumed:
                resumed.reserve_send("assemblyai", "POST", asr_category="upload")
                resumed.reserve_send("assemblyai", "POST", asr_category="job")
                with self.assertRaises(ValueError):
                    resumed.reserve_send("assemblyai", "POST", asr_category="job")
                resumed.reserve_send("assemblyai", "GET")
                self.assertEqual(resumed.jobs["job"], 2)

    def test_second_process_cannot_share_live_paid_journal(self):
        with tempfile.TemporaryDirectory() as directory, journal(Path(directory) / "journal.json") as first:
            with self.assertRaises(ValueError):
                ValidationBudgetJournal(first.path, CAPS)
            self.assertIsNone(first.reserve_hive(HiveV3Budget().reserve, "image"))

    def test_invalid_old_paid_journal_cannot_reset_or_guess_reservations(self):
        invalid = (
            {}, {"counts": {"hive": 1}, "events": [{"provider": "hive", "request_number": 1, "method": "POST"}]},
            {"counts": {"gemini": True}, "events": []},
            {"counts": {"unknown": 1}, "events": []},
            {"hive_reservations": {"image_requests": 0, "audio_seconds": 6, "audio_jobs": 1}},
            {"hive_reservations": {"image_requests": 0, "audio_seconds": 1, "audio_jobs": 0}},
            {"hive_paid_caps": {"image_requests": 20, "audio_seconds": 60, "audio_jobs": 1}},
            {"counts": {}, "events": [], "private_body": "never-serialize"},
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.json"
            for record in invalid:
                with self.subTest(record=record):
                    path.write_text(json.dumps(record))
                    with self.assertRaises(ValueError):
                        ValidationBudgetJournal(path, CAPS)
                    self.assertEqual(json.loads(path.read_text()), record)

    def test_journal_contains_only_sanitized_budget_metadata(self):
        with tempfile.TemporaryDirectory() as directory, journal(Path(directory) / "journal.json") as value:
            self.assertIsNone(value.reserve_hive(HiveV3Budget().reserve, "audio", 5))
            value.reserve_send("hive", "POST")
            record = json.loads(value.path.read_text())
            self.assertEqual(set(record), {"scope", "events", "counts", "caps", "asr_jobs", "hive_reservations", "hive_paid_caps"})
            self.assertEqual(set(record["events"][0]), {"provider", "request_number", "method", "transport_status"})
            for forbidden in ("api_key", "Authorization", "transcription", "media", "https://", "token", "DATABASE_URL"):
                self.assertNotIn(forbidden, value.path.read_text())


PUBLIC_URL = "https://www.royal.uk/the-king"


def public_document(**changes):
    return {"url": PUBLIC_URL, "title": "Public test article", "sentences": ["A complete public test sentence."],
            "sentence_roles": ["body"], "truncated": False,
            "retrieved_at": "2026-10-14T12:00:00+00:00", **changes}


class SourceDiagnosticTests(unittest.IsolatedAsyncioTestCase):
    def test_curated_https_urls_reject_query_fragment_credentials_and_other_hosts(self):
        self.assertEqual(diagnostic_source_url(PUBLIC_URL), PUBLIC_URL)
        for url in (PUBLIC_URL + "?token=private-marker", PUBLIC_URL + "#private-marker", PUBLIC_URL + "?",
                    "https://user:private-marker@www.royal.uk/the-king", "http://www.royal.uk/the-king",
                    "https://www.royal.uk.evil.test/the-king", "https://127.0.0.1/the-king",
                    "https://www.royal.uk:8443/the-king", "https://www.royal.uk/the king"):
            with self.subTest(url=url):
                self.assertIsNone(diagnostic_source_url(url))

    def test_article_contract_discards_headers_tokens_unknown_fields_and_private_url(self):
        value = diagnostic_document(public_document(headers={"Authorization": "private-marker"}, snapshot_token="private-marker"))
        self.assertEqual(value, public_document())
        self.assertNotIn("private-marker", json.dumps(value))
        self.assertIsNone(diagnostic_document(public_document(url=PUBLIC_URL + "?token=private-marker")))
        self.assertIsNone(diagnostic_document(public_document(sentences=["a" * 50001])))
        self.assertIsNone(diagnostic_document(public_document(retrieved_at="private-marker")))

    def test_publication_date_retained_without_inventing_missing_legacy_metadata(self):
        for published in (None, "2021-12-25"):
            document = public_document(publication_date=published)
            self.assertEqual(diagnostic_document(document), document)
        self.assertNotIn("publication_date", diagnostic_document(public_document()))
        for published in (True, {}, "2021-02-30", "2021-1-1", "private-marker", "2021-12-25T12:00:00"):
            self.assertIsNone(diagnostic_document(public_document(publication_date=published)))

    def test_public_media_provenance_retained_bounded_and_without_unknown_fields(self):
        for provenance in ({}, {"version": "visible_media_credits_v1", "media_credit_fragments": ["Foto: Reuters"]}):
            document = public_document(editorial_provenance=provenance)
            self.assertEqual(diagnostic_document(document), document)
        for provenance in (None, [], {"version": "private-marker", "media_credit_fragments": []},
                {"version": "visible_media_credits_v1", "media_credit_fragments": [False]},
                {"version": "visible_media_credits_v1", "media_credit_fragments": ["x" * 4001]},
                {"version": "visible_media_credits_v1", "media_credit_fragments": [""] * 65},
                {"version": "visible_media_credits_v1", "media_credit_fragments": [], "token": "private-marker"}):
            self.assertIsNone(diagnostic_document(public_document(editorial_provenance=provenance)))

    async def test_temporal_and_provenance_fields_survive_fixed_scope_restart(self):
        document = public_document(publication_date="2021-12-25", editorial_provenance={
            "version": "visible_media_credits_v1", "media_credit_fragments": ["Foto: Reuters"]})
        with tempfile.TemporaryDirectory() as directory:
            diagnostics = PublicSourceDiagnostics(directory)
            async def capture():
                diagnostics.record_article(PUBLIC_URL, document)
            await diagnostics.run_scoped(capture, "queen_true")
            resumed = PublicSourceDiagnostics(directory)
            self.assertEqual(resumed.records["documents"][0]["document"], document)

    async def test_unscoped_private_inputs_produce_no_diagnostic_file(self):
        with tempfile.TemporaryDirectory() as directory:
            value = PublicSourceDiagnostics(directory)
            resource = FetchedResource(b"private-body-marker", "text/html", PUBLIC_URL, "utf-8")
            value.record_fetch(PUBLIC_URL, resource)
            value.record_article(PUBLIC_URL, public_document(sentences=["private-body-marker"]))
            value.record_search("private-query-marker", NewsSearch([{"link": PUBLIC_URL}]))
            self.assertEqual(list(Path(directory).iterdir()), [])

    async def test_fixed_scope_retains_public_body_and_hash_not_raw_query_or_provider_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            value = PublicSourceDiagnostics(directory)
            async def capture():
                value.record_fetch(PUBLIC_URL, FetchedResource(b"<p>Public test sentence.</p>", "text/html", PUBLIC_URL, "utf-8"))
                value.record_article(PUBLIC_URL, public_document(headers={"Authorization": "private-marker"}))
                value.record_search(DIAGNOSTIC_TEXT_CONTROLS["queen_true"], NewsSearch([
                    {"link": PUBLIC_URL, "headers": {"Authorization": "private-marker"}, "title": "private-marker"},
                    {"link": PUBLIC_URL + "?token=private-marker"}, {"link": "https://evil.test/private-marker"}]))
            await value.run_scoped(capture, "queen_true")
            searches = json.loads(value.paths["searches"].read_text())
            self.assertEqual(searches[0]["leads"], [{"url": PUBLIC_URL}])
            self.assertEqual(len(searches[0]["query_sha256"]), 64)
            self.assertNotIn(DIAGNOSTIC_TEXT_CONTROLS["queen_true"], value.paths["searches"].read_text())
            for path in Path(directory).glob("*.json"):
                self.assertNotIn("private-marker", path.read_text())
            self.assertIsNone(value.scope.get())

    async def test_private_parallel_request_cannot_inherit_other_request_public_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            value = PublicSourceDiagnostics(directory)
            async def capture(query):
                await asyncio.sleep(0)
                value.record_search(query, NewsSearch([{"link": PUBLIC_URL}]))
            await asyncio.gather(
                value.run_scoped(capture, "queen_true", DIAGNOSTIC_TEXT_CONTROLS["queen_true"]),
                value.run_scoped(capture, None, "private-query-marker"),
            )
            rows = json.loads(value.paths["searches"].read_text())
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["scope"], "queen_true")
            self.assertIsNone(value.scope.get())

    async def test_scope_reset_survives_cancellation_or_error(self):
        with tempfile.TemporaryDirectory() as directory:
            value = PublicSourceDiagnostics(directory)
            async def fail():
                self.assertEqual(value.scope.get(), "queen_true")
                raise asyncio.CancelledError()
            with self.assertRaises(asyncio.CancelledError):
                await value.run_scoped(fail, "queen_true")
            self.assertIsNone(value.scope.get())

    async def test_restart_loads_v2_and_preserves_v1_and_existing_bodies(self):
        with tempfile.TemporaryDirectory() as directory:
            legacy = Path(directory) / "public-search-leads.json"
            legacy.write_text("legacy-private-marker-not-read")
            value = PublicSourceDiagnostics(directory)
            async def capture_first():
                value.record_fetch(PUBLIC_URL, FetchedResource(b"first public HTML", "text/html", PUBLIC_URL, "utf-8"))
            await value.run_scoped(capture_first, "queen_true")
            resumed = PublicSourceDiagnostics(directory)
            async def capture_second():
                resumed.record_fetch(PUBLIC_URL, FetchedResource(b"second public HTML", "text/html", PUBLIC_URL, "utf-8"))
            await resumed.run_scoped(capture_second, "queen_false")
            self.assertEqual((Path(directory) / "source-body-v2-1.html").read_bytes(), b"first public HTML")
            self.assertEqual((Path(directory) / "source-body-v2-2.html").read_bytes(), b"second public HTML")
            self.assertEqual(legacy.read_text(), "legacy-private-marker-not-read")
            self.assertEqual(len(PublicSourceDiagnostics(directory).records["bodies"]), 2)

    def test_orphan_body_and_private_or_malformed_manifest_fail_closed(self):
        invalid = (
            {"scope": "private-marker", "query_sha256": "a" * 64, "status": "success", "leads": []},
            {"scope": "queen_true", "query_sha256": "a" * 64, "status": "success", "leads": [{"url": PUBLIC_URL + "?token=private-marker"}]},
            {"scope": "queen_true", "query_sha256": "a" * 64, "status": "success", "leads": [], "query": "private-marker"},
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "public-source-searches-v2.json"
            for row in invalid:
                path.write_text(json.dumps([row]))
                with self.assertRaises(ValueError):
                    PublicSourceDiagnostics(directory)
            path.write_text("[]")
            documents = Path(directory) / "public-source-documents-v2.json"
            documents.write_text(json.dumps([{"scope": "queen_true", "requested_url": PUBLIC_URL, "document": None}]))
            with self.assertRaises(ValueError):
                PublicSourceDiagnostics(directory)
            documents.write_text("[]")
            (Path(directory) / "source-body-v2-1.html").write_bytes(b"unmatched public body")
            with self.assertRaises(ValueError):
                PublicSourceDiagnostics(directory)

    async def test_requested_or_final_query_url_is_never_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            value = PublicSourceDiagnostics(directory)
            async def capture():
                value.record_fetch(PUBLIC_URL + "?private-marker", FetchedResource(b"public", "text/html", PUBLIC_URL, "utf-8"))
                value.record_fetch(PUBLIC_URL, FetchedResource(b"public", "text/html", PUBLIC_URL + "?private-marker", "utf-8"))
                value.record_article(PUBLIC_URL + "?private-marker", public_document())
                value.record_article(PUBLIC_URL, public_document(url=PUBLIC_URL + "?private-marker"))
            await value.run_scoped(capture, "queen_true")
            self.assertEqual(list(Path(directory).iterdir()), [])

    async def test_installed_retrieval_scope_requires_exact_fixed_public_input(self):
        from app.core import pipeline
        from app.services import source_attribution
        class FakeApp:
            def get(self, _path):
                return lambda endpoint: endpoint
            post = get
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(pipeline, "search_web", new=AsyncMock(return_value=NewsSearch([{"link": PUBLIC_URL}]))), \
                patch.object(source_attribution, "fetch_public_resource", new=AsyncMock()), \
                patch.object(source_attribution, "_fetch_article", new=AsyncMock()), \
                patch.object(pipeline, "_retrieve_source_attribution") as original:
            async def retrieve(text, *_args, **_kwargs):
                await pipeline.search_web(text)
                return {"status": "success"}
            original.side_effect = retrieve
            diagnostics = install_source_diagnostics(FakeApp(), directory)
            await pipeline._retrieve_source_attribution(DIAGNOSTIC_TEXT_CONTROLS["queen_true"], [], None)
            await pipeline._retrieve_source_attribution(DIAGNOSTIC_TEXT_CONTROLS["queen_true"] + " private-marker", [], None)
            rows = json.loads(diagnostics.paths["searches"].read_text())
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["scope"], "queen_true")
            self.assertIsNone(diagnostics.scope.get())

    async def test_fixed_endpoint_claims_attempt_before_call_and_never_retries(self):
        from app.core import pipeline
        from app.services import source_attribution
        from fastapi import HTTPException
        class FakeApp:
            endpoint = None
            def post(self, _path):
                return lambda endpoint: endpoint
            def get(self, _path):
                def register(endpoint):
                    self.endpoint = endpoint
                    return endpoint
                return register
        fake_app = FakeApp()
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(pipeline, "search_web", new=AsyncMock()), \
                patch.object(pipeline, "_retrieve_source_attribution", new=AsyncMock()), \
                patch.object(source_attribution, "fetch_public_resource", new=AsyncMock()), \
                patch.object(source_attribution, "_fetch_article", new=AsyncMock(return_value=public_document())) as article:
            install_source_diagnostics(fake_app, directory)
            response = await fake_app.endpoint("royal")
            self.assertEqual(response["status"], "read")
            with self.assertRaises(HTTPException) as conflict:
                await fake_app.endpoint("royal")
            self.assertEqual(conflict.exception.status_code, 409)
            with self.assertRaises(HTTPException) as missing:
                await fake_app.endpoint("../private-marker")
            self.assertEqual(missing.exception.status_code, 404)
            self.assertEqual(article.await_count, 1)

    async def test_cached_component_is_not_automatic_discovery_and_cannot_repeat(self):
        from app.core import pipeline
        from app.services import source_attribution
        from fastapi import HTTPException
        from scripts.validation_ui_server import DIAGNOSTIC_FIXED_SOURCES
        class FakeApp:
            endpoint = None
            def get(self, _path):
                return lambda endpoint: endpoint
            def post(self, _path):
                def register(endpoint):
                    self.endpoint = endpoint
                    return endpoint
                return register
        app = FakeApp()
        result = {"status": "success", "state": "refuted", "coverage": {}, "provider_coverage": {}}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(pipeline, "search_web", new=AsyncMock()) as search, \
                patch.object(pipeline, "_retrieve_source_attribution", new=AsyncMock()), \
                patch.object(source_attribution, "fetch_public_resource", new=AsyncMock()) as fetch, \
                patch.object(source_attribution, "_fetch_article", new=AsyncMock()), \
                patch("app.services.source_corroboration.corroborate_sources", new=AsyncMock(return_value=result)) as compare:
            for name, url in DIAGNOSTIC_FIXED_SOURCES.items():
                (Path(directory) / f"source-control-{name}.json").write_text(json.dumps(public_document(url=url)))
            install_source_diagnostics(app, directory)
            response = await app.endpoint()
            self.assertIn("NOT_automatic_retrieval_or_UI", response["scope"])
            compare.assert_awaited_once()
            search.assert_not_awaited()
            fetch.assert_not_awaited()
            with self.assertRaises(HTTPException) as blocked:
                await app.endpoint()
            self.assertEqual(blocked.exception.status_code, 409)
