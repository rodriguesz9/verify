"""Bounded decoding of untrusted uploads; MIME/filename are not evidence."""
import asyncio
import io
import json
import math
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

MAX_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 20_000_000
MAX_DURATION = 120


@dataclass
class ValidatedMedia:
    data: bytes
    filename: str
    mime_type: str
    kind: str
    details: dict = field(default_factory=dict)


async def run_media_tool(*args: str, timeout: float = 15) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        proc.kill()
        await proc.communicate()
        raise
    if proc.returncode:
        raise ValueError("Não foi possível decodificar a mídia.")
    return stdout


def _inspect_image(data: bytes) -> dict:
    with Image.open(io.BytesIO(data)) as img:
        if img.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
            raise HTTPException(415, "Use JPEG, PNG, WebP ou GIF.")
        if img.width * img.height > MAX_PIXELS:
            raise HTTPException(413, "Imagem excede o limite de 20 megapixels.")
        details = {"width": img.width, "height": img.height,
                   "frames": getattr(img, "n_frames", 1), "format": img.format}
        img.verify()
    # Verify alone does not decode JPEG pixels.
    with Image.open(io.BytesIO(data)) as img:
        img.load()
    return details


async def _duration_from_probe(probe: dict, path: Path) -> float:
    # MediaRecorder WebM often has no duration in its container header.
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "video" and int(stream.get("width", 0)) * int(stream.get("height", 0)) > MAX_PIXELS:
            raise HTTPException(413, "Resolução de vídeo muito grande.")
    values = [probe.get("format", {}).get("duration"), *[s.get("duration") for s in probe.get("streams", [])]]
    durations = [float(v) for v in values if v not in (None, "N/A", "")]
    if any(not math.isfinite(v) or v < 0 for v in durations):
        raise ValueError("Duração inválida.")
    duration = max(durations, default=0)
    if duration > 0:
        return duration
    if not shutil.which("ffmpeg"):
        raise HTTPException(503, "Leitura de gravações indisponível: instale FFmpeg no servidor.")
    progress = await run_media_tool("ffmpeg", "-v", "error", "-xerror", "-nostdin", "-threads", "1",
        "-protocol_whitelist", "file,pipe", "-i", str(path), "-t", str(MAX_DURATION + 1),
        "-progress", "pipe:1", "-stats_period", "5", "-f", "null", "-")
    times = [int(line.split("=", 1)[1]) / 1_000_000 for line in progress.decode().splitlines() if line.startswith("out_time_us=")]
    return max(times, default=0)


async def validate_media(data: bytes, filename: str = "upload", mime_type: str = "") -> ValidatedMedia:
    if not data:
        raise HTTPException(422, "Arquivo vazio.")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Arquivo muito grande. Máximo: 25 MB.")
    filename = Path((filename or "upload").replace("\\", "/")).name[:180]
    declared = (mime_type or "").split(";", 1)[0].lower()
    image_signature = data.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF87a", b"GIF89a")) or (
        data.startswith(b"RIFF") and data[8:12] == b"WEBP")
    if image_signature:
        try:
            details = await asyncio.to_thread(_inspect_image, data)
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise HTTPException(422, "Imagem corrompida ou inválida.")
        actual = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif"}[details["format"]]
        kind = "image"
    else:
        audio_signature = data.startswith((b"ID3", b"OggS", b"fLaC")) or (
            data.startswith(b"RIFF") and data[8:12] == b"WAVE") or (
            len(data) > 1 and data[0] == 0xff and data[1] & 0xe0 == 0xe0)
        container_signature = data[4:8] == b"ftyp" or data.startswith(b"\x1a\x45\xdf\xa3")
        if not (audio_signature or container_signature):
            code = 422 if declared.startswith(("image/", "audio/", "video/")) else 415
            raise HTTPException(code, "O arquivo não é uma imagem, áudio ou vídeo válido.")
        if not shutil.which("ffprobe"):
            raise HTTPException(503, "Leitura de áudio/vídeo indisponível: instale FFmpeg no servidor.")
        try:
            with tempfile.TemporaryDirectory(prefix="verify-media-") as directory:
                path = Path(directory) / "input.bin"
                path.write_bytes(data)
                output = await run_media_tool("ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
                    "-show_streams", "-show_format", "-of", "json", str(path))
                probe = json.loads(output)
                duration = await _duration_from_probe(probe, path)
            streams = probe.get("streams", [])
            video = next((s for s in streams if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")), None)
            audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
            if not video and not audio:
                raise ValueError("Sem faixas de mídia.")
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError("Duração inválida.")
            if duration > MAX_DURATION:
                raise HTTPException(413, "Envie até 2 minutos de áudio ou vídeo.")
            if video and int(video.get("width", 0)) * int(video.get("height", 0)) > MAX_PIXELS:
                raise HTTPException(413, "Resolução de vídeo muito grande.")
            kind = "video" if video else "audio"
            container = probe.get("format", {}).get("format_name", "")
            actual = ("video/webm" if "webm" in container else "video/mp4") if video else (
                "audio/wav" if "wav" in container else "audio/ogg" if "ogg" in container else
                "audio/webm" if "webm" in container else "audio/flac" if "flac" in container else
                "audio/mp4" if "mov" in container else "audio/aac" if "aac" in container else "audio/mpeg")
            details = {"duration_seconds": duration, "has_audio": bool(audio), "has_video": bool(video),
                       "width": video.get("width") if video else None, "height": video.get("height") if video else None}
            if video:
                try:
                    numerator, denominator = video.get("avg_frame_rate", "0/1").split("/")
                    rate = float(numerator) / float(denominator)
                    if math.isfinite(rate) and 0 < rate <= 1000:
                        details["video_frame_rate"] = rate
                except (ValueError, ZeroDivisionError, TypeError, AttributeError):
                    pass
                try:
                    video_duration = float(video.get("duration", duration))
                    if math.isfinite(video_duration) and 0 < video_duration <= duration:
                        details["video_duration_seconds"] = video_duration
                except (ValueError, TypeError):
                    pass
        except (ValueError, KeyError, TypeError, asyncio.TimeoutError):
            raise HTTPException(422, "Áudio/vídeo corrompido ou não decodificável.")
    # Reject a spoofed media family, but infer generic uploads and MIME aliases.
    # Browsers label .webm as video/webm even when ffprobe finds audio only.
    # This narrowly scoped container alias is allowed AFTER real decoding;
    # it does not accept video tracks in audio endpoints or disguised images.
    audio_only_webm_alias = kind == "audio" and actual == "audio/webm" and declared == "video/webm"
    if declared.startswith(("image/", "audio/", "video/")) and declared.split("/")[0] != kind and not audio_only_webm_alias:
        raise HTTPException(415, "O tipo declarado não corresponde ao conteúdo do arquivo.")
    return ValidatedMedia(data, filename, actual, kind, details)


async def read_media(file: UploadFile, allowed_kind: str | None = None) -> ValidatedMedia:
    data = await file.read(MAX_BYTES + 1)
    media = await validate_media(data, file.filename, file.content_type)
    if allowed_kind and media.kind != allowed_kind:
        raise HTTPException(415, f"Este recurso aceita apenas {allowed_kind}.")
    return media


async def extract_video_frames(media: ValidatedMedia) -> list[tuple[float, bytes]]:
    if not shutil.which("ffmpeg"):
        raise HTTPException(503, "Análise de vídeo indisponível: FFmpeg não instalado.")
    duration = media.details.get("video_duration_seconds", media.details["duration_seconds"])
    try:
        maximum = min(12, max(3, int(os.getenv("VIDEO_MAX_FRAMES", "9"))))
    except ValueError:
        maximum = 9
    count = min(maximum, max(3, math.ceil(duration / 15) + 1))
    rate = media.details.get("video_frame_rate")
    last_frame = max(0, duration - 1 / rate) if rate else duration
    # Container duration includes the last frame's display interval, not a frame
    # starting at that endpoint. Short/low-FPS clips must not seek past it.
    timestamps = sorted(set(round(min(last_frame, duration * (.1 + .8 * i / (count - 1))), 3) for i in range(count)))
    frames = []
    with tempfile.TemporaryDirectory(prefix="verify-frames-") as directory:
        path = Path(directory) / "video.bin"
        path.write_bytes(media.data)
        for timestamp in timestamps:
            try:
                frame = await run_media_tool("ffmpeg", "-v", "error", "-nostdin", "-threads", "1",
                    "-protocol_whitelist", "file,pipe", "-ss", str(timestamp), "-i", str(path),
                    "-frames:v", "1", "-vf", "scale=768:768:force_original_aspect_ratio=decrease",
                    "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1")
                if not frame:
                    raise ValueError("Quadro vazio")
                frames.append((timestamp, frame))
            except (ValueError, asyncio.TimeoutError):
                raise HTTPException(422, "Não foi possível extrair quadros do vídeo.")
    return frames


async def extract_video_audio(media: ValidatedMedia) -> bytes:
    """Private, bounded mono PCM for actual audio detectors. No URL publishing."""
    if not media.details.get("has_audio"):
        return b""
    with tempfile.TemporaryDirectory(prefix="verify-audio-track-") as directory:
        path = Path(directory) / "video.bin"
        path.write_bytes(media.data)
        audio = await run_media_tool("ffmpeg", "-v", "error", "-nostdin", "-threads", "1",
            "-protocol_whitelist", "file,pipe", "-i", str(path), "-vn", "-t", str(MAX_DURATION),
            "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1")
        if not audio or len(audio) > MAX_BYTES:
            raise ValueError("Faixa de áudio indisponível")
        return audio
