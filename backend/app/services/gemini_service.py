"""Compatibility consolidation and optional real speech generation."""
import asyncio
import base64
import io
import json
import os
import re
import struct
import wave
import httpx
from app.services.evidence_policy import media_report, forensic_contract


_TTS_MAX_AUDIO_BYTES = 12 * 1024 * 1024
_TTS_MAX_BASE64_CHARS = ((_TTS_MAX_AUDIO_BYTES + 2) // 3) * 4
_TTS_MAX_RESPONSE_BYTES = _TTS_MAX_BASE64_CHARS + 64 * 1024
_TTS_MAX_DURATION_SECONDS = 120
_TTS_UNAVAILABLE_MESSAGE = "Fala indisponível no provedor. Nenhum áudio simulado foi produzido."


def _tts_unavailable(status, http_status=None):
    result = {"available": False, "status": status, "message": _TTS_UNAVAILABLE_MESSAGE}
    if http_status is not None:
        result["http_status"] = http_status
    return result


def _tts_mime(mime):
    """Accept the provider's PCM16LE formats, never guess compressed encodings."""
    if not isinstance(mime, str) or len(mime) > 200:
        raise ValueError("Invalid audio MIME")
    sections = mime.lower().split(";")
    media_type = sections[0].strip()
    if media_type not in {"audio/l16", "audio/wav", "audio/x-wav"}:
        raise ValueError("Unsupported audio MIME")
    parameters = {}
    for section in sections[1:]:
        key, separator, value = section.strip().partition("=")
        key, value = key.strip(), value.strip()
        if not separator or key in parameters or key not in {"rate", "channels", "codec", "bits"}:
            raise ValueError("Invalid audio MIME parameter")
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        if key == "codec":
            if value not in {"pcm", "pcm_s16le", "s16le"}:
                raise ValueError("Unsupported PCM encoding")
        else:
            if not re.fullmatch(r"[0-9]{1,5}", value):
                raise ValueError("Invalid PCM parameter")
            value = int(value)
            if ((key == "rate" and not 8000 <= value <= 48000)
                    or (key == "channels" and value not in {1, 2})
                    or (key == "bits" and value != 16)):
                raise ValueError("Unsupported PCM parameter")
        parameters[key] = value
    return media_type, parameters


def _tts_wav_info(raw):
    """Validate RIFF lengths and PCM headers before trusting WAV frame counts."""
    if (len(raw) < 44 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE"
            or struct.unpack_from("<I", raw, 4)[0] + 8 != len(raw)):
        raise ValueError("Invalid WAV container")
    offset, fmt, samples = 12, None, None
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise ValueError("Incomplete WAV chunk")
        chunk_id = raw[offset:offset + 4]
        chunk_size = struct.unpack_from("<I", raw, offset + 4)[0]
        start, end = offset + 8, offset + 8 + chunk_size
        next_offset = end + chunk_size % 2
        if next_offset > len(raw):
            raise ValueError("Truncated WAV chunk")
        if chunk_id == b"fmt ":
            if fmt is not None or samples is not None or chunk_size < 16:
                raise ValueError("Ambiguous WAV format")
            encoding, channels, rate, byte_rate, alignment, bits = struct.unpack_from("<HHIIHH", raw, start)
            if (encoding != 1 or channels not in {1, 2} or not 8000 <= rate <= 48000
                    or bits != 16 or alignment != channels * 2 or byte_rate != rate * alignment):
                raise ValueError("Unsupported WAV format")
            fmt = channels, rate, alignment
        elif chunk_id == b"data":
            if fmt is None or samples is not None or chunk_size == 0 or chunk_size % fmt[2]:
                raise ValueError("Invalid WAV samples")
            samples = chunk_size
        offset = next_offset
    if fmt is None or samples is None:
        raise ValueError("Missing WAV audio")
    channels, rate, alignment = fmt
    duration = samples / (rate * alignment)
    if not 0 < duration <= _TTS_MAX_DURATION_SECONDS:
        raise ValueError("WAV duration out of bounds")
    # A standard decoder must agree with the validated RIFF headers and samples.
    with wave.open(io.BytesIO(raw), "rb") as wav:
        if (wav.getcomptype() != "NONE" or wav.getsampwidth() != 2
                or wav.getnchannels() != channels or wav.getframerate() != rate
                or wav.getnframes() * alignment != samples
                or len(wav.readframes(wav.getnframes())) != samples):
            raise ValueError("Inconsistent WAV duration")
    return duration, rate, channels


def _tts_audio_to_wav(inline):
    if not isinstance(inline, dict):
        raise ValueError("Invalid inline audio")
    mime, parameters = _tts_mime(inline.get("mimeType"))
    encoded = inline.get("data")
    if not isinstance(encoded, str) or not 0 < len(encoded) <= _TTS_MAX_BASE64_CHARS:
        raise ValueError("Empty or oversized audio")
    raw = base64.b64decode(encoded, validate=True)
    if (not raw or len(raw) > _TTS_MAX_AUDIO_BYTES
            or base64.b64encode(raw).decode("ascii") != encoded):
        raise ValueError("Invalid audio payload")
    if mime in {"audio/wav", "audio/x-wav"}:
        duration, rate, channels = _tts_wav_info(raw)
        if (parameters.get("rate", rate) != rate or parameters.get("channels", channels) != channels):
            raise ValueError("WAV MIME disagrees with header")
        # Unary WAV is already a complete container. Do not prepend another one.
        return raw, duration
    rate, channels = parameters.get("rate", 24000), parameters.get("channels", 1)
    if ((raw[:4] == b"RIFF" and raw[8:12] == b"WAVE") or len(raw) % (channels * 2)):
        raise ValueError("Invalid raw PCM16 samples")
    duration = len(raw) / (rate * channels * 2)
    if not 0 < duration <= _TTS_MAX_DURATION_SECONDS:
        raise ValueError("PCM duration out of bounds")
    # Gemini's audio/l16 output is signed *little-endian* PCM, unlike the generic
    # RFC L16 network convention. Preserve actual provider samples unchanged.
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(raw)
    return output.getvalue(), duration


async def consolidate_forensic_report(filename, metadata_res, c2pa_res, detection_res, context_res, audio_res=None):
    # A language model is not allowed to invent new detector evidence or certainty.
    layers = {**detection_res, "metadata": metadata_res, "c2pa": c2pa_res, "context": context_res}
    return forensic_contract(media_report(layers, "audio" if audio_res else "image"))


async def get_ai_voice_speech(text="Olá! Esta é uma demonstração de fala gerada por IA."):
    if not isinstance(text, str) or not text.strip():
        return _tts_unavailable("invalid_input")
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return {"available": False, "status": "no_api_key", "message": "Gemini não configurado."}
    model = os.getenv("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts").strip()
    if not re.fullmatch(r"[a-zA-Z0-9._-]{1,120}", model):
        return _tts_unavailable("invalid_configuration")
    try:
        # Bound the complete request and streamed JSON, not only decoded audio.
        async with asyncio.timeout(20):
            async with httpx.AsyncClient(timeout=20, trust_env=False, follow_redirects=False) as client:
                async with client.stream("POST", f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={"x-goog-api-key": key}, json={
                    "contents": [{"parts": [{"text": text[:1500]}]}],
                    "generationConfig": {"responseModalities": ["AUDIO"],
                        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}}}}) as response:
                    if response.status_code != 200:
                        status = "rate_limited" if response.status_code == 429 else "unavailable" if response.status_code == 503 else "error"
                        return _tts_unavailable(status, response.status_code)
                    chunks, received = [], 0
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        received += len(chunk)
                        if received > _TTS_MAX_RESPONSE_BYTES:
                            return _tts_unavailable("invalid_response")
                        chunks.append(chunk)
        payload = json.loads(b"".join(chunks))
        candidate = payload["candidates"][0]
        if candidate.get("finishReason") not in {None, "STOP"}:
            return _tts_unavailable("invalid_response")
        parts = candidate["content"]["parts"]
        if not isinstance(parts, list) or not 1 <= len(parts) <= 64:
            return _tts_unavailable("invalid_response")
        audio = [part["inlineData"] for part in parts
                 if isinstance(part, dict) and not part.get("thought") and "inlineData" in part]
        if len(audio) != 1:
            return _tts_unavailable("invalid_response")
        wav_data, duration = _tts_audio_to_wav(audio[0])
        return {"available": True, "status": "success", "mime_type": "audio/wav",
                "audio_data": base64.b64encode(wav_data).decode("ascii"),
                "duration_sec": duration, "model_used": model}
    except (httpx.TimeoutException, TimeoutError):
        return _tts_unavailable("timeout")
    except httpx.HTTPError:
        return _tts_unavailable("error")
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, wave.Error, struct.error):
        return _tts_unavailable("invalid_response")
