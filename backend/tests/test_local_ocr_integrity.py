"""Literal TSV recognition and bounded, cancellation-safe local OCR."""
import asyncio
from pathlib import Path
import os
import unittest
from unittest.mock import AsyncMock, patch

from helpers import valid_png
from app.services import local_ocr


HEADER = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tconf\ttext\n"


def tsv(lines):
    rows = [HEADER]
    for line_number, words in enumerate(lines, 1):
        for word_number, word in enumerate(words, 1):
            rows.append(f"5\t1\t1\t1\t{line_number}\t{word_number}\t95\t{word}\n")
    return "".join(rows).encode()


class FakeProcess:
    def __init__(self, stdout=b"", stderr=b"", *, completed=True, kill_race=False):
        self.stdout, self.stderr = asyncio.StreamReader(), asyncio.StreamReader()
        self.stdout.feed_data(stdout)
        self.stderr.feed_data(stderr)
        self.returncode = 0 if completed else None
        if completed:
            self.stdout.feed_eof()
            self.stderr.feed_eof()
        self.exited = asyncio.Event()
        self.wait_started = asyncio.Event()
        self.kill_race = kill_race
        self.kill_count = 0
        self.reaped = False
        self.input_path = None
        self.input_existed_when_killed = None

    async def wait(self):
        self.wait_started.set()
        if self.returncode is None:
            await self.exited.wait()
        self.reaped = True
        return self.returncode

    def kill(self):
        self.kill_count += 1
        self.input_existed_when_killed = self.input_path.exists()
        self.returncode = 0 if self.kill_race else -9
        self.stdout.feed_eof()
        self.stderr.feed_eof()
        self.exited.set()
        if self.kill_race:
            raise ProcessLookupError()


class LocalOcrLiteralTests(unittest.TestCase):
    def test_quoted_negation_keeps_every_word_value_date_and_next_line(self):
        raw = tsv([['"Não', 'pague', 'R$', '123,45', 'em', '03/10/2026."'],
                   ['"Nunca', 'envie', 'senha."']])
        self.assertEqual(local_ocr._parse_tsv(raw),
            ('"Não pague R$ 123,45 em 03/10/2026."\n"Nunca envie senha."', True))

    def test_literal_double_quotes_and_apostrophes_are_not_csv_escapes(self):
        self.assertEqual(local_ocr._parse_tsv(tsv([['""Aviso""', "d'água", '“Não”']])),
            ('""Aviso"" d\'água “Não”', True))

    def test_missing_duplicate_or_extra_fields_never_produce_partial_text(self):
        valid = tsv([['Não', 'pague']])
        broken = [
            b'',
            valid.replace(b'word_num\t', b'', 1),
            valid.replace(b'conf\t', b'text\t', 1),
            valid + b'5\t1\t1\t1\t2\t1\t95\tvalor\textra\n',
            valid + b'5\t1\t1\t1\t2\t1\t95\n',
            valid + b'6\t1\t1\t1\t2\t1\t95\tvalor\n',
        ]
        for raw in broken:
            with self.subTest(raw_length=len(raw)), self.assertRaises(ValueError):
                local_ocr._parse_tsv(raw)

    def test_invalid_utf8_and_nonfinite_confidence_never_produce_text(self):
        valid = tsv([['Não', 'pague']])
        for raw in (valid + b'\xff', valid.replace(b'\t95\t', b'\tnan\t', 1),
                    valid.replace(b'\t95\t', b'\tinf\t', 1)):
            with self.subTest(raw_length=len(raw)), self.assertRaises(ValueError):
                local_ocr._parse_tsv(raw)

    def test_text_limit_rejects_instead_of_truncating(self):
        with self.assertRaises(ValueError):
            local_ocr._parse_tsv(tsv([['x' * 12001]]))


class LocalOcrProcessTests(unittest.IsolatedAsyncioTestCase):
    def setup_patches(self, process):
        async def spawn(_binary, input_name, *_args, **_kwargs):
            process.input_path = Path(input_name)
            self.assertTrue(process.input_path.is_file())
            return process
        return (patch.dict(os.environ, {'LOCAL_OCR_ENABLED': 'true'}),
                patch('app.services.local_ocr.shutil.which', return_value='/test/tesseract'),
                patch('app.services.local_ocr.asyncio.create_subprocess_exec', new=AsyncMock(side_effect=spawn)))

    async def test_success_preserves_quoted_text_without_any_remote_provider(self):
        process = FakeProcess(tsv([['"Não', 'pague', 'R$', '123,45."']]))
        environment, binary, spawn = self.setup_patches(process)
        with environment, binary, spawn:
            result = await local_ocr.extract_local_text(valid_png())
        self.assertEqual(result['text'], '"Não pague R$ 123,45."')
        self.assertEqual(result['status'], 'success')
        self.assertTrue(process.reaped)
        self.assertFalse(process.input_path.exists())

    async def test_output_overflow_stops_child_before_removing_private_input(self):
        process = FakeProcess(b'x' * (local_ocr.MAX_OCR_OUTPUT_BYTES + 1), completed=False)
        environment, binary, spawn = self.setup_patches(process)
        with environment, binary, spawn:
            result = await local_ocr.extract_local_text(valid_png())
        self.assertFalse(result['available'])
        self.assertEqual(result['text'], '')
        self.assertEqual(result['status'], 'invalid_response')
        self.assertEqual(process.kill_count, 1)
        self.assertTrue(process.input_existed_when_killed)
        self.assertTrue(process.reaped)
        self.assertFalse(process.input_path.parent.exists())

    async def test_stderr_overflow_is_bounded_and_never_echoed(self):
        process = FakeProcess(stderr=b'PRIVATE-ERROR ' * 6000, completed=False)
        environment, binary, spawn = self.setup_patches(process)
        with environment, binary, spawn:
            result = await local_ocr.extract_local_text(valid_png())
        self.assertEqual(result['status'], 'invalid_response')
        self.assertNotIn('PRIVATE-ERROR', str(result))
        self.assertEqual(process.kill_count, 1)
        self.assertTrue(process.reaped)

    async def test_caller_cancellation_reaps_child_then_removes_input(self):
        process = FakeProcess(completed=False)
        environment, binary, spawn = self.setup_patches(process)
        with environment, binary, spawn:
            task = asyncio.create_task(local_ocr.extract_local_text(valid_png()))
            await process.wait_started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(process.kill_count, 1)
        self.assertTrue(process.input_existed_when_killed)
        self.assertTrue(process.reaped)
        self.assertFalse(process.input_path.parent.exists())

    async def test_timeout_returns_no_partial_text_and_reaps_child(self):
        process = FakeProcess(completed=False)
        environment, binary, spawn = self.setup_patches(process)
        with environment, binary, spawn, patch('app.services.local_ocr._collect_output',
                new=AsyncMock(side_effect=TimeoutError)):
            result = await local_ocr.extract_local_text(valid_png())
        self.assertEqual(result['status'], 'timeout')
        self.assertEqual(result['text'], '')
        self.assertEqual(process.kill_count, 1)
        self.assertTrue(process.reaped)
        self.assertTrue(process.input_existed_when_killed)

    async def test_exit_race_does_not_replace_timeout_with_process_lookup_error(self):
        process = FakeProcess(completed=False, kill_race=True)
        environment, binary, spawn = self.setup_patches(process)
        with environment, binary, spawn, patch('app.services.local_ocr._collect_output',
                new=AsyncMock(side_effect=TimeoutError)):
            result = await local_ocr.extract_local_text(valid_png())
        self.assertEqual(result['status'], 'timeout')
        self.assertTrue(process.reaped)
