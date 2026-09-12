"""
OpenRouter integration — provides alternative AI analysis via openrouter.ai.
Can be used alongside or instead of Gemini for specific tasks.

Set OPENROUTER_API_KEY in .env to enable.
Set OPENROUTER_MODEL to override the default model.
"""

import asyncio
import json
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODEL = "google/gemini-2.0-flash-001"

FALLBACK_MODELS = [
    "google/gemini-2.0-flash-001",
    "anthropic/claude-3-haiku",
    "openai/gpt-4o-mini",
    "meta-llama/llama-3.1-8b-instruct",
]


class OpenRouterRotator:
    _index = 0
    _lock = asyncio.Lock()

    @classmethod
    async def get_model(cls) -> str:
        custom = os.getenv("OPENROUTER_MODEL", "").strip()
        if custom:
            return custom

        async with cls._lock:
            model = FALLBACK_MODELS[cls._index % len(FALLBACK_MODELS)]
            cls._index = (cls._index + 1) % len(FALLBACK_MODELS)
            return model

    @classmethod
    def get_current_model_name(cls) -> str:
        custom = os.getenv("OPENROUTER_MODEL", "").strip()
        return custom or FALLBACK_MODELS[cls._index % len(FALLBACK_MODELS)]


async def generate(
    prompt: str,
    system_instruction: str = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    """Generate a response via OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY não configurada")

    model = await OpenRouterRotator.get_model()

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://verify.app",
        "X-Title": "Verify - Fact Checker",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"]


async def generate_text(
    prompt: str,
    system_instruction: str = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str:
    """Generate plain text (no JSON) via OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY não configurada")

    model = await OpenRouterRotator.get_model()

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://verify.app",
        "X-Title": "Verify - Fact Checker",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"]


async def analyze_with_openrouter(text: str) -> dict:
    """Full analysis using OpenRouter as the AI backend."""
    system = (
        "Você é um analista de desinformação e golpes digitais. "
        "Analise o texto fornecido e retorne um JSON com: "
        '{"verdict": "Authentic"|"Suspicious"|"Scam", '
        '"score": número de 0 a 100, '
        '"summary": "resumo em português", '
        '"plain_explanation": "explicação simples em português", '
        '"risk_signals": ["sinal 1", "sinal 2"], '
        '"recommendations": ["ação 1", "ação 2"]}'
    )

    prompt = f"Analise o seguinte conteúdo:\n\n{text}"

    try:
        raw = await generate(prompt, system_instruction=system)
        return json.loads(raw)
    except Exception as e:
        return {
            "verdict": "Suspicious",
            "score": 50,
            "summary": f"Erro na análise via OpenRouter: {str(e)[:80]}",
            "plain_explanation": "Não foi possível analisar com IA externa.",
            "error": True,
        }
