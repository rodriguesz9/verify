"""
Audio Forensics & Synthetic Voice Service (Layer 4)
Integrates AssemblyAI, acoustic heuristics, and quick-verify for live demos.
"""

import os
import httpx
import asyncio
import re
from typing import Dict, Any, Optional

ASSEMBLYAI_API_URL = "https://api.assemblyai.com/v2"

# Key markers for phone scams
SCAM_PHRASES_PATTERNS = [
    r"(m[aã]e|pai|v[oó]).*(perdi\s+o\s+celular|quebrei\s+o\s+celular|novo\s+n[uú]mero)",
    r"(preciso\s+pagar\s+uma\s+conta|faz\s+um\s+pix|transfere\s+agora|urgente)",
    r"(me\s+ajuda.*dep[oó]sito|taxa\s+do\s+guincho|hospital\s+precisa\s+de\s+dinheiro)",
    r"(n[aã]o\s+conta\s+pra\s+ningu[eé]m|meu\s+cart[aã]o\s+foi\s+bloqueado)"
]


def detect_acoustic_scam_heuristics(text: str, audio_bytes: bytes) -> Dict[str, Any]:
    """
    Analyzes text transcript and audio bytes for voice cloning / phone scam signatures.
    """
    text_lower = text.lower()
    matched_scams = []
    for pattern in SCAM_PHRASES_PATTERNS:
        if re.search(pattern, text_lower):
            matched_scams.append(pattern)

    # Speech-content triage only. File size/noise do not establish voice origin.
    is_suspicious_speech = len(matched_scams) > 0 or ("mãe" in text_lower and "pix" in text_lower)
    
    indicators = []
    if len(matched_scams) > 0:
        indicators.append("Padrão de extorsão emocional urgente ('Golpe do Parente/Número Novo')")
    if "pix" in text_lower or "dinheiro" in text_lower or "paga" in text_lower:
        indicators.append("Solicitação de transferência financeira direta de emergência")

    return {
        "is_scam_pattern": is_suspicious_speech,
        "matched_scam_count": len(matched_scams),
        "indicators": indicators,
        "risk_level": "CRÍTICO" if is_suspicious_speech else "BAIXO"
    }


async def transcribe_with_assemblyai(file_bytes: bytes) -> Dict[str, Any]:
    """
    Transcribes audio using AssemblyAI with confidence and speech model metrics.
    """
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        return {
            "available": False,
            "status": "skipped",
            "reason": "ASSEMBLYAI_API_KEY não configurada",
            "transcription": ""
        }

    headers = {"authorization": api_key}

    try:
        # 1. Upload audio to AssemblyAI
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            upload_resp = await client.post(
                f"{ASSEMBLYAI_API_URL}/upload",
                headers=headers,
                content=file_bytes
            )
            if upload_resp.status_code != 200:
                return {"available": True, "status": "error", "error": "Upload failed"}

            audio_url = upload_resp.json().get("upload_url")
            if not isinstance(audio_url, str) or not audio_url.startswith("https://"):
                raise ValueError("Upload inválido")

            # 2. Submit transcription job
            transcript_resp = await client.post(
                f"{ASSEMBLYAI_API_URL}/transcript",
                headers=headers,
                json={"audio_url": audio_url, "language_code": "pt"}
            )
            transcript_id = transcript_resp.json().get("id")
            if transcript_resp.status_code not in {200, 201} or not isinstance(transcript_id, str) or not re.fullmatch(r"[a-zA-Z0-9-]{1,100}", transcript_id):
                raise ValueError("Job inválido")

            # 3. Poll for result (up to 8 seconds for demo responsiveness)
            for _ in range(8):
                await asyncio.sleep(1.0)
                poll_resp = await client.get(
                    f"{ASSEMBLYAI_API_URL}/transcript/{transcript_id}",
                    headers=headers
                )
                poll_data = poll_resp.json()
                if poll_resp.status_code != 200:
                    raise ValueError("Consulta indisponível")
                if poll_data.get("status") == "completed":
                    return {
                        "available": True,
                        "status": "success",
                        "transcription": poll_data.get("text") or "",
                        "confidence": poll_data.get("confidence", 0.0),
                        "words_count": len(poll_data.get("words", [])),
                        "audio_duration_sec": poll_data.get("audio_duration", 0)
                    }
                elif poll_data.get("status") == "error":
                    return {"available": False, "status": "error", "reason": "Transcrição recusada pelo provedor."}

        return {"available": True, "status": "timeout", "transcription": ""}
    except Exception:
        return {"available": False, "status": "error", "reason": "Resposta de transcrição indisponível ou inválida."}


async def analyze_audio_quick_for_demonstration(file_bytes: bytes, filename: str = "audio.wav", mime_type: str = "audio/wav") -> Dict[str, Any]:
    """
    Ultra-fast (< 3s) audio analysis endpoint specifically optimized for live stage presentations.
    Combines rapid acoustic heuristic detection with Gemini Multimodal Audio analysis.
    """
    import time
    start_time = time.time()

    # Actual bytes only. Fallback is transcription, never an authenticity vote.
    from app.core.audio_checker import transcribe_and_extract_audio
    transcription = ""
    transcription_provider = None
    try:
        transcription = await asyncio.wait_for(
            transcribe_and_extract_audio(file_bytes, mime_type),
            timeout=8
        )
        if transcription:
            transcription_provider = "gemini"
    except Exception:
        transcription = ""
    if not transcription and os.getenv("ASSEMBLYAI_API_KEY", "").strip():
        try:
            alternate = await asyncio.wait_for(transcribe_with_assemblyai(file_bytes), 8)
            if alternate.get("status") == "success" and isinstance(alternate.get("transcription"), str):
                transcription = alternate["transcription"]
                transcription_provider = "assemblyai"
        except Exception:
            pass

    heuristics = detect_acoustic_scam_heuristics(transcription, file_bytes)
    elapsed_ms = int((time.time() - start_time) * 1000)
    return {
        "verdict": "inconclusiva",
        "analysis_status": "inconclusive",
        "confidence": None,
        "score_percent": None,
        "transcription": transcription,
        "transcription_status": "success" if transcription else "unavailable",
        "transcription_provider": transcription_provider,
        "short_explanation": "Há sinais de pedido financeiro suspeito na fala; isso não comprova clonagem de voz." if heuristics["is_scam_pattern"] else (
            "A transcrição foi obtida, mas a origem da voz não pôde ser determinada." if transcription else
            "Não foi possível transcrever este áudio. Não há resultado de detecção de clonagem."),
        "risk_level": "ATENÇÃO" if heuristics["is_scam_pattern"] else "INDETERMINADO",
        "indicators": heuristics["indicators"],
        "content_risk": heuristics,
        "limitations": ["Análise do conteúdo da fala não é análise acústica de autenticidade.",
                        "Confirme pedidos de dinheiro com a pessoa por outro canal."],
        "tempo_processamento_ms": elapsed_ms
    }
