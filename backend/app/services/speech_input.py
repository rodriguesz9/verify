"""Private mono PCM for transcription. Silence gate is not voice authentication."""
import array
import io
import shutil
import sys
import tempfile
import wave
from pathlib import Path
from app.services.media_validation import run_media_tool


def _native_mono_pcm(data):
    """Read only already-normalized PCM WAV, without a subprocess startup.

    Unsupported/truncated/compressed input never becomes a silence result;
    it follows the existing bounded decoder. Re-encoding below strips metadata.
    """
    try:
        with wave.open(io.BytesIO(data), "rb") as audio:
            frames = audio.getnframes()
            if (audio.getcomptype() != "NONE" or audio.getnchannels() != 1
                    or audio.getsampwidth() != 2 or audio.getframerate() != 16000
                    or not 0 < frames <= 16000 * 120):
                return None
            pcm = audio.readframes(frames + 1)
            return pcm if len(pcm) == frames * 2 else None
    except (wave.Error, EOFError, ValueError):
        return None


async def prepare_speech_input(data):
    if not data or len(data) > 25 * 1024 * 1024:
        raise ValueError("Audio limit")
    pcm = _native_mono_pcm(data)
    if pcm is None:
        if not shutil.which("ffmpeg"):
            return data, None, "unavailable"
        with tempfile.TemporaryDirectory(prefix="verify-speech-") as directory:
            path = Path(directory) / "input.bin"
            path.write_bytes(data)
            pcm = await run_media_tool("ffmpeg", "-v", "error", "-nostdin", "-threads", "1",
                "-protocol_whitelist", "file,pipe", "-i", str(path), "-vn", "-t", "120",
                "-ac", "1", "-ar", "16000", "-f", "s16le", "pipe:1", timeout=3)
    if not pcm or len(pcm) > 16000 * 2 * 120 or len(pcm) % 2:
        raise ValueError("Invalid audio output")
    samples = array.array("h", pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    # Below ~-72 dBFS: not enough signal to justify asking an LLM for words.
    # Does NOT claim that quiet recordings have no speech, or prove voice origin.
    near_silent = max(abs(sample) for sample in samples) <= 8
    out = io.BytesIO()
    with wave.open(out, "wb") as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
        audio.writeframes(pcm)
    return out.getvalue(), near_silent, "success"
