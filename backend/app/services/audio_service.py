"""Bounded speech transcription and content triage. Not voice authentication."""

import os
import asyncio
from app.core.gemini_client import gemini_timeout_seconds
import re
import time
from typing import Dict, Any
from app.services.assemblyai_jobs import assemblyai_jobs
from app.services.transcription_scope import current_transcription_scope

# Key markers for phone scams
SCAM_PHRASES_PATTERNS = [
    # Match the actual loss phrase, so a preceding "não" remains visible to
    # the negation guard. Starting at "mãe" previously hid that negation.
    r"(?:perdi|quebrei)\s+(?:o|meu)\s+celular|(?:troquei\s+de|meu\s+novo)\s+n[uú]mero",
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


async def transcribe_with_assemblyai(file_bytes: bytes) -> Dict[str, Any]:
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        return {"available": False, "status": "not_configured", "transcription": "",
                "reason": "ASSEMBLYAI_API_KEY não configurada."}
    return await assemblyai_jobs.transcribe(file_bytes, api_key, current_transcription_scope())


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
    # The local signal observation does not require a cloud key. A silent
    # recording must not become 'provider not configured' in the report.
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
                    text = await asyncio.wait_for(transcribe_and_extract_audio(file_bytes, mime_type), timeout=gemini_timeout_seconds() + 2)
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
            transcription_detail = {**{key: value for key, value in result.items() if key not in {"transcription", "words"}},
                                    "provider": provider}
            if provider == "assemblyai" and result.get("status") in {
                "pending", "in_progress", "blocked_uncertain", "blocked_expired", "capacity_exceeded",
            }:
                # Pending/unknown creation is not a failed transcription that
                # warrants another cloud submission to a different provider.
                break
            if result.get("status") == "success" and isinstance(result.get("transcription"), str) and result["transcription"].strip():
                transcription, transcription_provider = result["transcription"], provider
                break
        transcription_detail["attempts"] = attempts

    heuristics = detect_acoustic_scam_heuristics(transcription, file_bytes)
    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    pending_explanations = {
        "pending": "A transcrição ainda está pendente. Uma nova tentativa nesta sessão consultará a tarefa existente, dentro da janela de retomada. A origem da voz não foi determinada.",
        "in_progress": "Uma transcrição deste arquivo já está em andamento nesta sessão. Aguarde; nenhuma nova tarefa foi criada. A origem da voz não foi determinada.",
        "blocked_uncertain": "A criação da transcrição não pôde ser confirmada. Novo envio está temporariamente bloqueado para evitar duplicação. A origem da voz não foi determinada.",
        "blocked_expired": "A janela privada de retomada expirou, sem transcrição disponível. Nenhuma tarefa nova foi criada nesta janela. A origem da voz não foi determinada.",
        "capacity_exceeded": "O limite privado de transcrições foi atingido. Nenhuma tarefa nova foi criada para este pedido. A origem da voz não foi determinada.",
    }
    pending_status = transcription_detail.get("status") if transcription_detail.get("status") in pending_explanations else None
    return {
        "verdict": "inconclusiva",
        "analysis_status": "inconclusive",
        "confidence": None,
        "score_percent": None,
        "transcription": transcription,
        "transcription_status": "success" if transcription else "no_speech" if near_silent or transcription_detail.get("status") == "no_speech" else pending_status or "unavailable",
        "transcription_provider": transcription_provider,
        "transcription_detail": transcription_detail,
        "short_explanation": "Há sinais de pedido financeiro suspeito na fala; isso não comprova clonagem de voz." if heuristics["is_scam_pattern"] else (
            "A transcrição foi obtida, mas a origem da voz não pôde ser determinada." if transcription else
            "O sinal de áudio é silencioso ou muito baixo; nenhuma palavra foi inventada. Isso não determina a origem da voz." if near_silent else
            pending_explanations[pending_status] if pending_status else
            "Não foi possível transcrever este áudio. Não há resultado de detecção de clonagem."),
        "risk_level": "ATENÇÃO" if heuristics["is_scam_pattern"] else "INDETERMINADO",
        "indicators": heuristics["indicators"],
        "content_risk": heuristics,
        "limitations": ["Análise do conteúdo da fala não é análise acústica de autenticidade.",
                        "Confirme pedidos de dinheiro com a pessoa por outro canal."],
        "tempo_processamento_ms": elapsed_ms
    }
