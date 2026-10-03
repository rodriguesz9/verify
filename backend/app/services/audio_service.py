"""Bounded speech transcription and content triage. Not voice authentication."""

import os
import httpx
import asyncio
import re
import time
from typing import Dict, Any, Optional

ASSEMBLYAI_API_URL = "https://api.assemblyai.com/v2"

# Key markers for phone scams
SCAM_PHRASES_PATTERNS = [
    r"(m[aã]e|pai|v[oó]).*(perdi\s+o\s+celular|quebrei\s+o\s+celular|novo\s+n[uú]mero)",
    r"(preciso\s+pagar\s+uma\s+conta|(?:faz|fa[cç]a|transfere|transfira|envie)\s+(um\s+)?(pix|dinheiro))",
    r"(me\s+ajuda.*dep[oó]sito|taxa\s+do\s+guincho|hospital\s+precisa\s+de\s+dinheiro)",
    r"(n[aã]o\s+conta\s+pra\s+ningu[eé]m|meu\s+cart[aã]o\s+foi\s+bloqueado)"
]


def detect_acoustic_scam_heuristics(text: str, audio_bytes: bytes) -> Dict[str, Any]:
    """Legacy function name: only transcript patterns, never acoustic/clone proof."""
    text_lower = text.lower()
    from app.core.scam_detector import is_negated_request
    matched_scams = []
    for pattern in SCAM_PHRASES_PATTERNS:
        match = next((m for m in re.finditer(pattern, text_lower) if not is_negated_request(text_lower, m.start())), None)
        if match:
            matched_scams.append(match.group(0))

    # Speech-content triage only. File size/noise do not establish voice origin.
    is_suspicious_speech = len(matched_scams) > 0
    
    indicators = []
    if len(matched_scams) > 0:
        indicators.append("Há pedido financeiro ou relato de troca/perda de celular na fala. Isso não comprova golpe: confirme por outro canal.")

    return {
        "is_scam_pattern": is_suspicious_speech,
        "matched_scam_count": len(matched_scams),
        "indicators": indicators,
        "matched_excerpts": matched_scams,
        "risk_level": "ATENÇÃO" if is_suspicious_speech else "INDETERMINADO"
    }


async def _assemblyai_job(file_bytes: bytes, api_key: str) -> Dict[str, Any]:
    """
    Transcribes audio using AssemblyAI with confidence and speech model metrics.
    """
    headers = {"authorization": api_key}

    try:
        # 1. Upload audio to AssemblyAI
        async with httpx.AsyncClient(timeout=10.0, trust_env=False, follow_redirects=False) as client:
            upload_resp = await client.post(
                f"{ASSEMBLYAI_API_URL}/upload",
                headers=headers,
                content=file_bytes
            )
            if upload_resp.status_code != 200:
                return {"available": False, "status": "error", "reason": f"Upload AssemblyAI indisponível (HTTP {upload_resp.status_code})."}

            audio_url = upload_resp.json().get("upload_url")
            if not isinstance(audio_url, str) or not audio_url.startswith("https://"):
                raise ValueError("Upload inválido")

            # 2. Submit transcription job
            transcript_resp = await client.post(
                f"{ASSEMBLYAI_API_URL}/transcript",
                headers=headers,
                json={"audio_url": audio_url, "language_code": "pt", "speech_models": ["universal-2"]}
            )
            transcript_id = transcript_resp.json().get("id")
            if transcript_resp.status_code not in {200, 201} or not isinstance(transcript_id, str) or not re.fullmatch(r"[a-zA-Z0-9-]{1,100}", transcript_id):
                raise ValueError("Job inválido")

            # Poll immediately, then back off. The entire job has one deadline,
            # not a timeout shorter than its compulsory polling sleeps.
            for attempt in range(16):
                poll_resp = await client.get(
                    f"{ASSEMBLYAI_API_URL}/transcript/{transcript_id}",
                    headers=headers
                )
                poll_data = poll_resp.json()
                if poll_resp.status_code != 200:
                    raise ValueError("Consulta indisponível")
                if poll_data.get("status") == "completed":
                    text = poll_data.get("text")
                    if not isinstance(text, str) or not text.strip():
                        return {"available": False, "status": "no_speech", "transcription": "",
                                "reason": "O provedor não encontrou fala transcritível."}
                    if len(text) > 100000:
                        raise ValueError("Transcrição inválida")
                    return {
                        "available": True,
                        "status": "success",
                        "transcription": text.strip(),
                        "model_used": str(poll_data.get("speech_model_used") or "universal-2")[:100],
                        "decision_role": "transcription_only",
                        "confidence": poll_data.get("confidence", 0.0),
                        "words_count": len(poll_data.get("words", [])),
                        "audio_duration_sec": poll_data.get("audio_duration", 0)
                    }
                elif poll_data.get("status") == "error":
                    return {"available": False, "status": "error", "reason": "Transcrição recusada pelo provedor."}
                elif poll_data.get("status") not in {"queued", "processing"}:
                    raise ValueError("Estado inválido")
                await asyncio.sleep(min(.5 * (attempt + 1), 2))

        return {"available": False, "status": "pending", "transcription": "",
                "reason": "A tarefa de transcrição não concluiu a tempo. Não houve reenvio do áudio."}
    except Exception:
        return {"available": False, "status": "error", "reason": "Resposta de transcrição indisponível ou inválida."}


async def transcribe_with_assemblyai(file_bytes: bytes) -> Dict[str, Any]:
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        return {"available": False, "status": "not_configured", "transcription": "",
                "reason": "ASSEMBLYAI_API_KEY não configurada."}
    try:
        return await asyncio.wait_for(_assemblyai_job(file_bytes, api_key), timeout=25)
    except asyncio.TimeoutError:
        return {"available": False, "status": "pending", "transcription": "",
                "reason": "Transcrição não concluída no prazo. Tarefa não reenviada para evitar custo duplicado."}


async def analyze_audio_quick_for_demonstration(file_bytes: bytes, filename: str = "audio.wav", mime_type: str = "audio/wav") -> Dict[str, Any]:
    """
    Bounded transcription and speech-content triage, NOT an acoustic detector.
    """
    start_time = time.monotonic()

    # Actual bytes only. Fallback is transcription, never an authenticity vote.
    from app.core.audio_checker import transcribe_and_extract_audio
    transcription = ""
    transcription_provider = None
    transcription_detail = {"status": "not_configured"}
    near_silent = False
    if any(os.getenv(key, "").strip() for key in ("GEMINI_API_KEY", "ASSEMBLYAI_API_KEY")):
        from app.services.speech_input import prepare_speech_input
        try:
            prepared, near_silent, _ = await prepare_speech_input(file_bytes)
            if prepared != file_bytes:
                file_bytes, mime_type = prepared, "audio/wav"
        except (Exception, asyncio.TimeoutError):
            # Decode already validated upstream. Failed optimization is not evidence.
            pass
    preference = os.getenv("AUDIO_TRANSCRIPTION_PROVIDER", "gemini").strip().lower()
    order = ("assemblyai", "gemini") if preference == "assemblyai" else ("gemini", "assemblyai")
    attempts = []
    if near_silent:
        transcription_detail = {"status": "no_speech", "provider": "local_signal_gate",
            "reason": "Áudio silencioso ou com sinal muito baixo. Aumente o volume ou regrave; nenhuma API recebeu o áudio para inventar uma transcrição."}
    else:
        for provider in order:
            if provider == "assemblyai":
                if not os.getenv("ASSEMBLYAI_API_KEY", "").strip():
                    continue
                result = await transcribe_with_assemblyai(file_bytes)
            else:
                try:
                    text = await asyncio.wait_for(transcribe_and_extract_audio(file_bytes, mime_type), timeout=20)
                    result = {"available": bool(text), "status": "success" if text else "no_speech" if os.getenv("GEMINI_API_KEY", "").strip() else "not_configured",
                              "transcription": text, "model_used": getattr(text, "model_name", None)}
                except Exception as exc:
                    from app.core.gemini_client import GeminiError
                    result = {"available": False, "status": getattr(exc, "status", "timeout" if isinstance(exc, asyncio.TimeoutError) else "error"),
                              "reason": str(exc) if isinstance(exc, GeminiError) else "Transcrição Gemini não concluída no prazo."}
            attempts.append({"provider": provider, "status": result.get("status"), "reason": result.get("reason")})
            if result.get("status") == "not_configured" and len(attempts) > 1:
                # An absent fallback must not hide a real pending/error reason.
                continue
            transcription_detail = {key: value for key, value in result.items() if key not in {"transcription", "words"}}
            if result.get("status") == "success" and isinstance(result.get("transcription"), str) and result["transcription"].strip():
                transcription, transcription_provider = result["transcription"], provider
                break
        transcription_detail["attempts"] = attempts

    heuristics = detect_acoustic_scam_heuristics(transcription, file_bytes)
    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    return {
        "verdict": "inconclusiva",
        "analysis_status": "inconclusive",
        "confidence": None,
        "score_percent": None,
        "transcription": transcription,
        "transcription_status": "success" if transcription else "unavailable",
        "transcription_provider": transcription_provider,
        "transcription_detail": transcription_detail,
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
