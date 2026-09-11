import asyncio
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

async def transcribe_and_extract_audio(file_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """
    Uses Gemini Multimodal to transcribe and extract claims from WhatsApp voice notes or audio files.
    """
    model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
    # Clean model name if preview
    if "flash-lite-8b" in model_name or "3.1" in model_name:
        model_name = "gemini-1.5-flash"
        
    model = genai.GenerativeModel(model_name)
    
    prompt = """
Você é um assistente de checagem de fatos.
Ouça o áudio fornecido e transcreva fielmente o que a pessoa está falando em português do Brasil.
Retorne apenas o texto transcrito com clareza. Não adicione comentários extras.
"""
    
    try:
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
        print(f"Error transcribing audio with Gemini: {e}")
        return ""
