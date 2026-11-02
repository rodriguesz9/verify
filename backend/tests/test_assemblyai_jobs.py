"""Offline controls for scoped, finite-window transcription operations."""

import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.services.assemblyai_jobs import AssemblyAIJobs, PUBLIC_FIELDS


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class AssemblyJobsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.posts, self.polls = [], []
        self.poll_status, self.poll_http = "completed", 200
        self.upload_url = "https://cdn.assemblyai.com/upload/private-upload"
        self.submit_status, self.submit_id = 200, "private-job"
        self.submit_exception = None
        self.submit_entered, self.submit_release = None, None
        self.poll_entered, self.poll_release = None, None
        self.clock = FakeClock()
        self.store = AssemblyAIJobs(transport=httpx.MockTransport(self.handle), max_polls=1, clock=self.clock)

    async def asyncTearDown(self):
        await self.store.shutdown()

    async def handle(self, request):
        if request.method == "POST":
            self.posts.append(request.url.path)
            if request.url.path.endswith("/upload"):
                self.assertEqual(request.headers.get("content-type"), "application/octet-stream")
                return httpx.Response(200, json={"upload_url": self.upload_url})
            self.assertEqual(json.loads(request.content)["speech_models"], ["universal-2"])
            self.assertEqual(json.loads(request.content)["language_code"], "pt")
            if self.submit_entered is not None:
                self.submit_entered.set()
                await self.submit_release.wait()
            if self.submit_exception is not None:
                raise self.submit_exception
            return httpx.Response(self.submit_status, json={"id": self.submit_id})
        self.polls.append(request.url.path)
        if self.poll_entered is not None:
            self.poll_entered.set()
            await self.poll_release.wait()
        return httpx.Response(self.poll_http, json={"status": self.poll_status,
            "text": "Não pague R$ 123,45 em 03/10/2026.", "confidence": .98,
            "audio_duration": 2, "words": [], "id": "private-job",
            "audio_url": "private-upload-url", "private_key": "private-key", "error": "private-message"})

    async def transcribe(self, namespace="account:control-a", data=b"authorized-control", key="test-only-key"):
        return await self.store.transcribe(data, key, namespace)

    async def test_pending_retry_resumes_get_without_new_upload_or_job(self):
        self.poll_status = "queued"
        first = await self.transcribe()
        self.assertEqual(first["status"], "pending")
        self.poll_status = "completed"
        second = await self.transcribe()
        self.assertEqual(second["status"], "success")
        self.assertEqual(self.posts, ["/v2/upload", "/v2/transcript"])
        self.assertEqual(self.polls, ["/v2/transcript/private-job"] * 2)

    async def test_poll_503_preserves_checkpoint_for_later_get(self):
        self.poll_http = 503
        self.assertEqual((await self.transcribe())["status"], "pending")
        self.poll_http = 200
        self.assertEqual((await self.transcribe())["status"], "success")
        self.assertEqual(len(self.posts), 2)
        self.assertEqual(len(self.polls), 2)

    async def test_concurrent_same_scope_shares_single_operation(self):
        self.poll_entered, self.poll_release = asyncio.Event(), asyncio.Event()
        first = asyncio.create_task(self.transcribe())
        await self.poll_entered.wait()
        second = asyncio.create_task(self.transcribe())
        await asyncio.sleep(0)
        self.poll_release.set()
        results = await asyncio.gather(first, second)
        self.assertTrue(all(result["status"] == "success" for result in results))
        self.assertEqual(len(self.posts), 2)
        self.assertEqual(len(self.polls), 1)

    async def test_cancelling_requester_after_checkpoint_does_not_cancel_worker(self):
        self.poll_entered, self.poll_release = asyncio.Event(), asyncio.Event()
        first = asyncio.create_task(self.transcribe())
        await self.poll_entered.wait()
        record = next(iter(self.store._records.values()))
        self.assertEqual(record.job_id, "private-job")
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        self.assertFalse(record.task.cancelled())
        second = asyncio.create_task(self.transcribe())
        self.poll_release.set()
        self.assertEqual((await second)["status"], "success")
        self.assertEqual(len(self.posts), 2)
        self.assertEqual(len(self.polls), 1)

    async def test_requester_deadline_preserves_shared_operation(self):
        self.store.waiter_timeout = .01
        self.poll_entered, self.poll_release = asyncio.Event(), asyncio.Event()
        first = await self.transcribe()
        self.assertEqual(first["status"], "in_progress")
        self.store.waiter_timeout = 1
        self.poll_release.set()
        self.assertEqual((await self.transcribe())["status"], "success")
        self.assertEqual(len(self.posts), 2)
        self.assertEqual(len(self.polls), 1)

    async def test_worker_deadline_preserves_job_and_next_round_only_polls(self):
        self.store.worker_timeout = .01
        self.poll_entered, self.poll_release = asyncio.Event(), asyncio.Event()
        self.assertEqual((await self.transcribe())["status"], "pending")
        self.poll_release.set()
        self.assertEqual((await self.transcribe())["status"], "success")
        self.assertEqual(len(self.posts), 2)
        self.assertEqual(len(self.polls), 2)

    async def test_ambiguous_submission_timeout_does_not_resubmit(self):
        self.submit_exception = httpx.ReadTimeout("private-message")
        for _ in range(2):
            result = await self.transcribe()
            self.assertEqual(result["status"], "blocked_uncertain")
            self.assertNotIn("private-message", str(result))
        self.assertEqual(len(self.posts), 2)
        self.assertEqual(self.polls, [])

    async def test_requester_cancelled_during_submit_does_not_create_second_job(self):
        self.submit_entered, self.submit_release = asyncio.Event(), asyncio.Event()
        first = asyncio.create_task(self.transcribe())
        await self.submit_entered.wait()
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        second = asyncio.create_task(self.transcribe())
        self.submit_release.set()
        self.assertEqual((await second)["status"], "success")
        self.assertEqual(len(self.posts), 2)
        self.assertEqual(len(self.polls), 1)

    async def test_worker_deadline_during_submit_blocks_uncertain_creation(self):
        self.store.worker_timeout = .01
        self.submit_entered, self.submit_release = asyncio.Event(), asyncio.Event()
        self.assertEqual((await self.transcribe())["status"], "blocked_uncertain")
        self.assertEqual((await self.transcribe())["status"], "blocked_uncertain")
        self.assertEqual(len(self.posts), 2)
        self.assertEqual(self.polls, [])

    async def test_expiring_during_active_poll_does_not_send_get_with_missing_id(self):
        self.store.max_polls = 3
        self.poll_status = "queued"
        self.poll_entered, self.poll_release = asyncio.Event(), asyncio.Event()
        first = asyncio.create_task(self.transcribe())
        await self.poll_entered.wait()
        record = next(iter(self.store._records.values()))
        self.clock.now = record.retained_until
        self.store._prune()
        self.assertEqual(record.phase, "blocked_expired")
        with patch("app.services.assemblyai_jobs.asyncio.sleep", new=AsyncMock()):
            self.poll_release.set()
            self.assertEqual((await first)["status"], "blocked_expired")
        self.assertEqual(self.polls, ["/v2/transcript/private-job"])

    async def test_ambiguous_5xx_or_invalid_job_id_does_not_resubmit(self):
        for status, job_id in ((503, "private-job"), (200, "../../secret"), (200, None), (200, "x" * 101)):
            with self.subTest(status=status, invalid_id=job_id):
                await self.store.shutdown()
                self.submit_status, self.submit_id = status, job_id
                before = len(self.posts)
                self.assertEqual((await self.transcribe())["status"], "blocked_uncertain")
                self.assertEqual((await self.transcribe())["status"], "blocked_uncertain")
                self.assertEqual(len(self.posts) - before, 2)

    async def test_accounts_tabs_credentials_and_bytes_have_separate_namespaces(self):
        for namespace, data, key in (("account:a", b"same", "key1"),
                                     ("account:b", b"same", "key1"),
                                     ("anonymous:tab-a", b"same", "key1"),
                                     ("anonymous:tab-b", b"same", "key1"),
                                     ("account:a", b"same", "key2"),
                                     ("account:a", b"changed", "key1")):
            self.assertEqual((await self.transcribe(namespace, data, key))["status"], "success")
        self.assertEqual(len(self.posts), 12)
        keys = str(list(self.store._records))
        self.assertNotIn("account:a", keys)
        self.assertNotIn("key1", keys)

    async def test_absent_scope_never_reuses_a_global_file_hash(self):
        for _ in range(2):
            self.assertEqual((await self.transcribe(None))["status"], "success")
        self.assertEqual(len(self.posts), 4)

    async def test_capacity_refuses_new_job_without_evicting_pending(self):
        self.store.capacity = 1
        self.poll_status = "queued"
        self.assertEqual((await self.transcribe())["status"], "pending")
        self.assertEqual((await self.transcribe("account:other"))["status"], "capacity_exceeded")
        self.assertEqual(len(self.posts), 2)
        self.poll_status = "completed"
        self.assertEqual((await self.transcribe())["status"], "success")
        self.assertEqual(len(self.posts), 2)

    async def test_active_limit_refuses_new_background_operation(self):
        self.store.active_limit = 1
        self.poll_entered, self.poll_release = asyncio.Event(), asyncio.Event()
        first = asyncio.create_task(self.transcribe())
        await self.poll_entered.wait()
        result = await self.transcribe("account:other")
        self.assertEqual(result["status"], "capacity_exceeded")
        self.assertEqual(len(self.posts), 2)
        self.poll_release.set()
        await first

    async def test_pending_expiration_is_fixed_and_tombstone_does_not_resubmit(self):
        self.poll_status = "queued"
        await self.transcribe()
        record = next(iter(self.store._records.values()))
        deadline = record.retained_until
        self.clock.now += 100
        await self.transcribe()
        self.assertEqual(record.retained_until, deadline)
        self.clock.now = deadline
        self.assertEqual((await self.transcribe())["status"], "blocked_expired")
        self.assertIsNone(record.job_id)
        self.clock.now += 299
        self.assertEqual((await self.transcribe())["status"], "blocked_expired")
        self.assertEqual(len(self.posts), 2)
        self.clock.now += 1
        self.store._prune()
        self.assertEqual(len(self.store._records), 0)

    async def test_success_ttl_is_not_renewed_and_removal_erases_transcript(self):
        await self.transcribe()
        record = next(iter(self.store._records.values()))
        deadline = record.result_until
        self.clock.now += 299
        await self.transcribe()
        self.assertEqual(record.result_until, deadline)
        self.clock.now += 1
        self.store._prune()
        self.assertIsNone(record.result)
        self.assertIsNone(record.job_id)
        self.assertEqual(len(self.store._records), 0)

    async def test_idle_success_timer_erases_cache_without_new_request(self):
        await self.store.shutdown()
        self.store = AssemblyAIJobs(transport=httpx.MockTransport(self.handle), max_polls=1, success_ttl=.02)
        await self.transcribe()
        record = next(iter(self.store._records.values()))
        await asyncio.sleep(.04)
        self.assertIsNone(record.result)
        self.assertEqual(len(self.store._records), 0)

    async def test_idle_pending_timer_expires_then_removes_tombstone(self):
        await self.store.shutdown()
        self.store = AssemblyAIJobs(transport=httpx.MockTransport(self.handle), max_polls=1,
                                    pending_ttl=.02, tombstone_ttl=.03)
        self.poll_status = "queued"
        await self.transcribe()
        record = next(iter(self.store._records.values()))
        await asyncio.sleep(.03)
        self.assertEqual(record.phase, "blocked_expired")
        self.assertIsNone(record.job_id)
        await asyncio.sleep(.04)
        self.assertEqual(len(self.store._records), 0)

    async def test_public_results_are_whitelisted_independent_copies(self):
        first = await self.transcribe()
        self.assertLessEqual(set(first), PUBLIC_FIELDS)
        first["transcription"] = "changed by caller"
        first["private-field"] = "injected"
        second = await self.transcribe()
        self.assertEqual(second["transcription"], "Não pague R$ 123,45 em 03/10/2026.")
        serialized = json.dumps(second)
        for forbidden in ("private-job", "private-upload", "private-key", "private-message", "account:control-a", "injected"):
            self.assertNotIn(forbidden, serialized)

    async def test_invalid_upload_urls_are_rejected_before_job_submission(self):
        for url in ("http://cdn.assemblyai.com/upload/a", "https://cdn.assemblyai.com.evil.test/a",
                    "https://user@cdn.assemblyai.com/a", "https://cdn.assemblyai.com:444/a",
                    "https://cdn.assemblyai.com/a#secret", "https://evil.test/a"):
            with self.subTest(url=url):
                await self.store.shutdown()
                self.upload_url = url
                before = len(self.posts)
                self.assertEqual((await self.transcribe())["status"], "error")
                self.assertEqual(len(self.posts) - before, 1)

    async def test_shutdown_cancels_workers_timers_and_clears_records(self):
        self.poll_entered, self.poll_release = asyncio.Event(), asyncio.Event()
        first = asyncio.create_task(self.transcribe())
        await self.poll_entered.wait()
        record = next(iter(self.store._records.values()))
        timer = record.expiry_timer
        await self.store.shutdown()
        with self.assertRaises(asyncio.CancelledError):
            await first
        self.assertIsNone(record.result)
        self.assertIsNone(record.job_id)
        self.assertTrue(timer.cancelled())
        self.assertEqual(self.store._records, {})


class PendingFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_pending_or_blocked_assembly_does_not_submit_to_gemini(self):
        from app.services.audio_service import analyze_audio_quick_for_demonstration
        # audio_service imports this helper lazily, so load its module before
        # patching the current provider-preparation hook.
        from app.services import speech_input  # noqa: F401
        for status in ("pending", "in_progress", "blocked_uncertain", "blocked_expired", "capacity_exceeded"):
            with self.subTest(status=status), patch.dict(os.environ, {
                "ASSEMBLYAI_API_KEY": "test-only", "GEMINI_API_KEY": "test-only", "AUDIO_TRANSCRIPTION_PROVIDER": "assemblyai",
            }), patch("app.services.speech_input.prepare_speech_input", new=AsyncMock(return_value=(b"voice", False, "success"))), \
                    patch("app.services.audio_service.transcribe_with_assemblyai", new=AsyncMock(return_value={"available": False, "status": status, "reason": "Controlled pending"})), \
                    patch("app.core.audio_checker.transcribe_and_extract_audio", new=AsyncMock()) as gemini:
                result = await analyze_audio_quick_for_demonstration(b"voice")
                self.assertEqual(result["transcription_detail"]["status"], status)
                self.assertEqual(result["transcription_status"], status)
                self.assertEqual(result["transcription_detail"]["provider"], "assemblyai")
                self.assertEqual(result["analysis_status"], "inconclusive")
                self.assertEqual(result["transcription"], "")
                self.assertIsNone(result["confidence"])
                self.assertIn("origem da voz não foi determinada", result["short_explanation"])
                self.assertNotIn("Não foi possível transcrever", result["short_explanation"])
                self.assertEqual(result["indicators"], [])
                self.assertEqual(len(result["transcription_detail"]["attempts"]), 1)
                gemini.assert_not_awaited()
