import asyncio
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

MODEL_ROTATION = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-lite",
]

class GeminiModelRotator:
    _index = 0
    _lock = asyncio.Lock()

    @classmethod
    async def get_model(cls) -> genai.GenerativeModel:
        async with cls._lock:
            model_name = MODEL_ROTATION[cls._index % len(MODEL_ROTATION)]
            cls._index = (cls._index + 1) % len(MODEL_ROTATION)
            return genai.GenerativeModel(model_name)

    @classmethod
    def get_current_model_name(cls) -> str:
        return MODEL_ROTATION[cls._index % len(MODEL_ROTATION)]


def _extract_audio_features(audio_bytes: bytes) -> dict:
    """Extract acoustic features that may indicate synthetic speech."""
    try:
        import numpy as np
        import librosa
        import io
        audio_stream = io.BytesIO(audio_bytes)
        y, sr = librosa.load(audio_stream, sr=None, mono=True)

        f0, voiced_flag, voiced_probs = librosa.pyin(
            y,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            sr=sr
        )
        f0 = f0[~np.isnan(f0)]

        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

        features = {
            "duration": len(y) / sr,
            "sample_rate": sr,
            "f0_mean": float(np.mean(f0)) if len(f0) > 0 else 0.0,
            "f0_std": float(np.std(f0)) if len(f0) > 0 else 0.0,
            "f0_range": float(np.max(f0) - np.min(f0)) if len(f0) > 0 else 0.0,
            "spectral_centroid_mean": float(np.mean(spectral_centroids)),
            "spectral_rolloff_mean": float(np.mean(spectral_rolloff)),
            "zcr_mean": float(np.mean(zero_crossing_rate)),
            "mfcc_mean": [float(np.mean(mfccs[i])) for i in range(13)],
            "spectral_flux": float(np.mean(np.diff(librosa.feature.rms(y=y)))),
            "energy": float(np.mean(librosa.feature.rms(y=y))),
        }

        synth_score = 0.0
        if features["f0_std"] < 20 and features["duration"] > 1.0:
            synth_score += 0.3
        if features["energy"] < 0.01:
            synth_score += 0.2
        if features["spectral_centroid_mean"] > 4000:
            synth_score += 0.2

        features["synthetic_speech_score"] = min(1.0, synth_score)
        return features
    except Exception as e:
        print(f"Audio feature extraction failed: {e}")
        return {
            "error": str(e),
            "synthetic_speech_score": 0.0,
            "duration": 0.0,
        }


async def transcribe_and_extract_audio(file_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """
    Uses Gemini Multimodal to transcribe and extract claims from WhatsApp voice notes or audio files.
    Implements round-robin model rotation for load distribution.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return ""
    genai.configure(api_key=api_key)
    try:
        model = await GeminiModelRotator.get_model()
        prompt = """
        Você é um assistente de checagem de fatos.
        Ouça o áudio fornecido e transcreva fielmente o que a pessoa está falando em português do Brasil.
        Retorne apenas o texto transcrito com clareza. Não adicione comentários extras.
        """
        audio_part = {
            "mime_type": mime_type,
            "data": file_bytes
        }
        response = await asyncio.to_thread(
            model.generate_content,
            [prompt, audio_part]
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error transcribing audio with Gemini (model: {GeminiModelRotator.get_current_model_name()}): {e}")
        try:
            model = await GeminiModelRotator.get_model()
            audio_part = {
                "mime_type": mime_type,
                "data": file_bytes
            }
            prompt = """
            Você é um assistente de checagem de fatos.
            Transcreva fielmente o que a pessoa está falando em português do Brasil.
            Retorne apenas o texto transcrito.
            """
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt, audio_part]
            )
            return response.text.strip()
        except Exception:
            return ""