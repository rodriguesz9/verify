"""Audio container/transport controls only: fixtures are not human voice samples."""
import base64
import io
import json
import os
import struct
import unittest
import wave
from unittest.mock import patch

import helpers  # disable provider keys before importing application modules
import httpx
from app.services import gemini_service as service


_ASYNC_CLIENT = httpx.AsyncClient
_PCM = b"\x01\x00\x02\x00\xfd\xff\xff\xff" * 100


def wav_control(samples=_PCM, rate=24000, channels=1, width=2):
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        wav.writeframes(samples)
    return output.getvalue()


def inline_audio(raw, mime="audio/l16;codec=pcm;rate=24000"):
    return {"mimeType": mime, "data": base64.b64encode(raw).decode("ascii")}


def response_body(inline):
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"inlineData": inline}]}}]}


class TtsFormatTests(unittest.IsolatedAsyncioTestCase):
    async def call_provider(self, body=None, status=200, text="Esta fala é um controle.", handler_error=None, model="gemini-3.8-flash-tts"):
        self.requests = []
        self.client_options = []

        def handler(request):
            self.requests.append(request)
            if handler_error:
                raise handler_error("private-provider-debug", request=request)
            return httpx.Response(status, json=body, request=request)

        def factory(**options):
            self.client_options.append(options)
            return _ASYNC_CLIENT(transport=httpx.MockTransport(handler), **options)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "offline-test-placeholder", "GEMINI_TTS_MODEL": model}), \
                patch.object(service.httpx, "AsyncClient", side_effect=factory):
            return await service.get_ai_voice_speech(text)

    def assert_no_audio(self, result, status="invalid_response"):
        self.assertFalse(result["available"])
        self.assertEqual(result["status"], status)
        self.assertNotIn("audio_data", result)
        self.assertNotIn("duration_sec", result)
        self.assertNotIn("private-provider-debug", json.dumps(result))

    def assert_wav_samples(self, result, expected, rate=24000, channels=1):
        self.assertTrue(result["available"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mime_type"], "audio/wav")
        raw = base64.b64decode(result["audio_data"], validate=True)
        with wave.open(io.BytesIO(raw), "rb") as wav:
            self.assertEqual(wav.getnchannels(), channels)
            self.assertEqual(wav.getframerate(), rate)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertEqual(wav.readframes(wav.getnframes()), expected)
        self.assertAlmostEqual(result["duration_sec"], len(expected) / (rate * channels * 2))
        return raw

    async def test_lowercase_l16_is_wrapped_once_with_original_little_endian_samples(self):
        result = await self.call_provider(response_body(inline_audio(_PCM)))
        self.assert_wav_samples(result, _PCM)
        self.assertEqual(result["model_used"], "gemini-3.8-flash-tts")

    async def test_legacy_uppercase_l16_and_case_insensitive_parameters_work(self):
        result = await self.call_provider(response_body(inline_audio(_PCM, ' AuDiO/L16; CoDeC=PCM; RaTe="24000"; CHANNELS=1; BITS=16 ')))
        self.assert_wav_samples(result, _PCM)

    async def test_l16_defaults_remain_mono_24khz(self):
        result = await self.call_provider(response_body(inline_audio(_PCM, "audio/l16")))
        self.assert_wav_samples(result, _PCM)

    async def test_explicit_stereo_rate_controls_valid_pcm_duration(self):
        result = await self.call_provider(response_body(inline_audio(_PCM, "audio/l16;rate=16000;channels=2")))
        self.assert_wav_samples(result, _PCM, rate=16000, channels=2)

    async def test_unary_wav_bytes_are_preserved_without_an_extra_header(self):
        source = wav_control()
        result = await self.call_provider(response_body(inline_audio(source, "audio/wav")))
        actual = self.assert_wav_samples(result, _PCM)
        self.assertEqual(actual, source)

    async def test_wav_rate_and_stereo_are_read_from_actual_header(self):
        source = wav_control(rate=48000, channels=2)
        result = await self.call_provider(response_body(inline_audio(source, "Audio/WAV;rate=48000;channels=2")))
        self.assertEqual(self.assert_wav_samples(result, _PCM, 48000, 2), source)

    async def test_standard_x_wav_alias_preserves_valid_wav(self):
        source = wav_control()
        result = await self.call_provider(response_body(inline_audio(source, "audio/x-wav")))
        self.assertEqual(self.assert_wav_samples(result, _PCM), source)

    async def test_wav_unknown_bounded_metadata_chunk_does_not_change_samples(self):
        source = wav_control()
        metadata = b"JUNK" + struct.pack("<I", 4) + b"test"
        source = source[:4] + struct.pack("<I", len(source) + len(metadata) - 8) + source[8:] + metadata
        result = await self.call_provider(response_body(inline_audio(source, "audio/wav")))
        self.assertEqual(self.assert_wav_samples(result, _PCM), source)

    async def test_unsupported_or_ambiguous_mime_is_not_faked_into_voice(self):
        for mime in [None, {}, "audio/mp3", "audio/l160", "audio/l16;codec=mulaw",
                     "audio/l16;rate=0", "audio/l16;rate=99999", "audio/l16;rate=24k",
                     "audio/l16;rate=24000;rate=16000", "audio/l16;channels=0",
                     "audio/l16;channels=3", "audio/l16;bits=24", "audio/l16;unknown=1",
                     "audio/l16;rate", "audio/l16;", "audio/l16;rate=\"24000"]:
            with self.subTest(mime=mime):
                self.assert_no_audio(await self.call_provider(response_body(inline_audio(_PCM, mime))))

    async def test_strict_canonical_base64_required(self):
        for data in [None, {}, "", "!!!!", "AQ==\n", "data:audio/wav;base64,AQ==", "AQ", "AR=="]:
            with self.subTest(data=data):
                self.assert_no_audio(await self.call_provider(response_body({"mimeType": "audio/l16", "data": data})))

    async def test_audio_bytes_and_encoded_payload_are_bounded(self):
        with patch.object(service, "_TTS_MAX_AUDIO_BYTES", 16):
            self.assert_no_audio(await self.call_provider(response_body(inline_audio(_PCM))))
        with patch.object(service, "_TTS_MAX_BASE64_CHARS", 16):
            self.assert_no_audio(await self.call_provider(response_body(inline_audio(_PCM))))
        with patch.object(service, "_TTS_MAX_RESPONSE_BYTES", 16):
            self.assert_no_audio(await self.call_provider(response_body(inline_audio(_PCM))))

    async def test_response_stream_stops_at_limit_and_closes_without_reading_rest(self):
        state = {"yielded": 0, "closed": False}

        class BoundedControlStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                for _index in range(5):
                    state["yielded"] += 1
                    yield b"x" * 65536

            async def aclose(self):
                state["closed"] = True

        def factory(**options):
            return _ASYNC_CLIENT(transport=httpx.MockTransport(
                lambda request: httpx.Response(200, stream=BoundedControlStream(), request=request)), **options)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "offline-test-placeholder", "GEMINI_TTS_MODEL": "gemini-3.8-flash-tts"}), \
                patch.object(service.httpx, "AsyncClient", side_effect=factory), \
                patch.object(service, "_TTS_MAX_RESPONSE_BYTES", 16):
            result = await service.get_ai_voice_speech()
        self.assert_no_audio(result)
        self.assertEqual(state["yielded"], 1)
        self.assertTrue(state["closed"])

    async def test_raw_pcm_requires_complete_16_bit_frames(self):
        for raw, mime in [(b"\x01", "audio/l16"), (b"\x01\x00", "audio/l16;channels=2"),
                          (wav_control(), "audio/l16")]:
            with self.subTest(mime=mime, length=len(raw)):
                self.assert_no_audio(await self.call_provider(response_body(inline_audio(raw, mime))))

    async def test_declared_wav_must_really_be_a_decodable_wav(self):
        for raw in [_PCM, b"RIFF", b"RIFF" + b"\x00" * 40, wav_control()[:-1], wav_control() + b"extra"]:
            with self.subTest(length=len(raw)):
                self.assert_no_audio(await self.call_provider(response_body(inline_audio(raw, "audio/wav"))))

    async def test_wav_header_sizes_and_frame_alignment_must_match_data(self):
        source = wav_control()
        corruptions = []
        for offset, format, value in [(4, "<I", len(source)), (28, "<I", 1),
                                      (32, "<H", 1), (40, "<I", len(_PCM) + 2)]:
            raw = bytearray(source)
            struct.pack_into(format, raw, offset, value)
            corruptions.append(bytes(raw))
        for raw in corruptions:
            with self.subTest(raw_header=raw[:44]):
                self.assert_no_audio(await self.call_provider(response_body(inline_audio(raw, "audio/wav"))))

    async def test_wav_rejects_empty_unsupported_rate_or_bit_width(self):
        for raw in [wav_control(b""), wav_control(width=1), wav_control(width=3), wav_control(rate=96000)]:
            with self.subTest(length=len(raw)):
                self.assert_no_audio(await self.call_provider(response_body(inline_audio(raw, "audio/wav"))))

    async def test_wav_mime_parameters_must_agree_with_container(self):
        for mime in ["audio/wav;rate=16000", "audio/wav;channels=2"]:
            with self.subTest(mime=mime):
                self.assert_no_audio(await self.call_provider(response_body(inline_audio(wav_control(), mime))))

    async def test_audio_duration_limit_applies_to_pcm_and_wav(self):
        with patch.object(service, "_TTS_MAX_DURATION_SECONDS", 0.001):
            self.assert_no_audio(await self.call_provider(response_body(inline_audio(_PCM))))
            self.assert_no_audio(await self.call_provider(response_body(inline_audio(wav_control(), "audio/wav"))))

    async def test_duplicate_wav_data_chunk_is_rejected(self):
        source = wav_control()
        extra_data = b"data" + struct.pack("<I", 2) + b"\x01\x00"
        raw = source[:4] + struct.pack("<I", len(source) + len(extra_data) - 8) + source[8:] + extra_data
        self.assert_no_audio(await self.call_provider(response_body(inline_audio(raw, "audio/wav"))))

    async def test_partial_generation_or_missing_audio_does_not_return_success(self):
        truncated = response_body(inline_audio(_PCM))
        truncated["candidates"][0]["finishReason"] = "MAX_TOKENS"
        for body in [None, {}, {"candidates": []}, truncated,
                     {"candidates": [{"content": {"parts": [{"text": "no audio"}]}}]},
                     {"candidates": [{"content": {"parts": [{"thought": True, "inlineData": inline_audio(_PCM)}]}}]},
                     {"candidates": [{"content": {"parts": [{"inlineData": inline_audio(_PCM)}] * 2}}]}]:
            with self.subTest(body=body):
                self.assert_no_audio(await self.call_provider(body))

    async def test_one_audio_part_may_follow_text_without_being_confused(self):
        body = response_body(inline_audio(_PCM))
        body["candidates"][0]["content"]["parts"].insert(0, {"text": "audio output"})
        self.assert_wav_samples(await self.call_provider(body), _PCM)

    async def test_request_uses_configured_safe_model_and_exact_limited_transcript(self):
        transcript = "Fala em português. " * 150
        result = await self.call_provider(response_body(inline_audio(_PCM)), text=transcript)
        self.assert_wav_samples(result, _PCM)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0].url.path, "/v1beta/models/gemini-3.8-flash-tts:generateContent")
        body = json.loads(self.requests[0].content)
        self.assertEqual(body["contents"][0]["parts"][0]["text"], transcript[:1500])
        self.assertEqual(body["generationConfig"]["responseModalities"], ["AUDIO"])
        self.assertFalse(self.client_options[0]["trust_env"])
        self.assertFalse(self.client_options[0]["follow_redirects"])

    async def test_invalid_model_identifier_never_starts_request(self):
        for model in ["", "../other", "models/gemini-3.8-flash-tts", "model?key=private", "a" * 121]:
            with self.subTest(model=model):
                result = await self.call_provider(response_body(inline_audio(_PCM)), model=model)
                self.assert_no_audio(result, "invalid_configuration")
                self.assertEqual(self.requests, [])
                self.assertEqual(self.client_options, [])

    async def test_empty_or_non_text_input_never_starts_request(self):
        for text in [None, {}, "", " \n "]:
            with self.subTest(text=text):
                self.assert_no_audio(await self.call_provider(None, text=text), "invalid_input")
                self.assertEqual(self.requests, [])

    async def test_missing_api_key_never_starts_request_or_generates_beep(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}), \
                patch.object(service.httpx, "AsyncClient") as client:
            result = await service.get_ai_voice_speech()
        self.assert_no_audio(result, "no_api_key")
        client.assert_not_called()

    async def test_rate_limit_and_service_unavailable_are_explicit_without_retry(self):
        for http_status, result_status in [(429, "rate_limited"), (503, "unavailable")]:
            with self.subTest(http_status=http_status):
                result = await self.call_provider({"error": {"message": "private-provider-debug"}}, http_status)
                self.assert_no_audio(result, result_status)
                self.assertEqual(result["http_status"], http_status)
                self.assertEqual(len(self.requests), 1)

    async def test_auth_or_redirect_provider_errors_do_not_leak_body_or_retry(self):
        for status in [301, 401, 403, 404, 500]:
            with self.subTest(http_status=status):
                result = await self.call_provider({"private-provider-debug": "not returned"}, status)
                self.assert_no_audio(result, "error")
                self.assertEqual(len(self.requests), 1)

    async def test_timeout_and_connection_error_never_return_fabricated_audio(self):
        for error, status in [(httpx.ReadTimeout, "timeout"), (httpx.ConnectError, "error")]:
            with self.subTest(error=error):
                self.assert_no_audio(await self.call_provider(handler_error=error), status)
                self.assertEqual(len(self.requests), 1)

    async def test_total_deadline_timeout_has_no_audio_or_private_exception(self):
        with patch.object(service.asyncio, "timeout", side_effect=TimeoutError("private-provider-debug")):
            self.assert_no_audio(await self.call_provider(response_body(inline_audio(_PCM))), "timeout")
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
