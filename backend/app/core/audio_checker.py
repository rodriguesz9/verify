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
