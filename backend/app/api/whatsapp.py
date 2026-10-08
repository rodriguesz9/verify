from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any
import os
import hashlib
import hmac
import json
import logging
from app.core.pipeline import run_pipeline
from app.services.gemini_service import get_ai_voice_speech
from app.core.database import AsyncSessionLocal
from app.core.auth import get_optional_user
from app.models.user import User
from app.models.history import WhatsAppConversation
from app.services.public_fetch import fetch_public_resource
from app.services.whatsapp_security import (
    authenticate_webhook, decode_media, parse_message, receipts, MAX_MEDIA_BYTES,
)
from app.services.media_validation import validate_media
from app.services.media_analysis import analyze_media as analyze_validated_media
from app.services.transcription_scope import (
    request_transcription_scope, webhook_transcription_scope, transcription_scope,
    has_pending_transcription,
)

router = APIRouter()

class WhatsAppMessageRequest(BaseModel):
    message: str = Field(default="", max_length=5000)
    from_number: Optional[str] = Field(default=None, max_length=256)
    media_url: Optional[str] = Field(default=None, max_length=4096)
    media_type: Optional[str] = Field(default=None, max_length=100)
    want_voice_reply: bool = False
    @model_validator(mode="after")
    def valid_content(self):
        self.message = self.message.strip()
        if not self.media_url and len(self.message) < 10:
            raise ValueError("Envie pelo menos 10 caracteres ou uma mídia.")
        return self

def _hash_sender(sender: str) -> str:
    """Pseudonymize with a server secret; phone numbers are easily guessable."""
    secret = os.getenv("WHATSAPP_HASH_SECRET", "")
    if len(secret) < 32:
        raise ValueError("WhatsApp history hashing secret not configured")
    return hmac.new(secret.encode(), sender.encode(), hashlib.sha256).hexdigest()

async def download_media(media_url: str, expected_type: str = "audio") -> bytes:
    """Baixa mídia via HTTP(S) com limites de tamanho e tempo."""
    if not media_url:
        raise HTTPException(status_code=400, detail="media_url é obrigatório para mídia.")
    resource = await fetch_public_resource(media_url, max_bytes=MAX_MEDIA_BYTES)
    return resource.data

def format_whatsapp_response(report: Dict[str, Any], query_preview: str = "") -> str:
    verdict = report.get("verdict", "Suspicious")
    score = report.get("score", 50)
    summary = report.get("summary", "")
    plain_explanation = report.get("plain_explanation", "")
    elderly_tip = report.get("elderly_tip", "")
    
    # Verdict visual badges
    if report.get("analysis_status") == "inconclusive":
        badge = "🔎 *ANÁLISE INCONCLUSIVA*"
        score_text = "Origem/veracidade não determinada; não é prova de falsificação."
    elif verdict == "Authentic":
        badge = "📚 *INFORMAÇÃO CORROBORADA NAS FONTES CONSULTADAS*"
        score_text = "Confira as referências. Isso não garante autenticidade de uma mídia."
    elif verdict == "False":
        badge = "📚 *AFIRMAÇÃO REFUTADA NAS CHECAGENS CONSULTADAS*"
        score_text = "Compare afirmação, data e argumentos nas fontes originais."
    elif verdict == "Scam":
        badge = "🚨 *CUIDADO: ALERTA DE GOLPE / FRAUDE*"
        score_text = "Há padrões de possível golpe. Confirme pelo canal oficial antes de agir."
    elif verdict in ["Manipulated", "AI_Generated"]:
        badge = "🔎 *INDÍCIOS DE IA / POSSÍVEL MANIPULAÇÃO*"
        score_text = "Indícios não comprovam falsidade da informação nem intenção de enganar."
    elif verdict == "Out_Of_Context":
        badge = "🔍 *FORA DE CONTEXTO / HISTÓRIA ANTIGA*"
        score_text = "Confira a data e o contexto na fonte original."
    else:
        badge = "⚠️ *SUSPEITO / NÃO CONFIRMADO*"
        score_text = "As evidências disponíveis não permitem concluir."

    msg_lines = [
        "━━━━━━━━━━━━━━━━━━",
        "🔍 *VERIFY - Checagem de Fatos*",
        "━━━━━━━━━━━━━━━━━━",
        "",
        f"📊 *Veredito:* {badge}",
        f"📈 *{score_text}*",
        "",
        "📝 *O QUE VOCÊ PRECISA SABER:*",
        f"{summary or plain_explanation}",
        ""
    ]

    if elderly_tip:
        msg_lines.extend([
            "💡 *DICA DE SEGURANÇA:*",
            f"{elderly_tip}",
            ""
        ])

    red_flags = report.get("red_flags", [])
    if red_flags:
        msg_lines.append("⚠️ *Pontos de Atenção:*")
        for flag in red_flags[:2]:
            msg_lines.append(f"• {flag}")
        msg_lines.append("")

    msg_lines.extend([
        "━━━━━━━━━━━━━━━━━━",
        "🛡️ *Dica:* Antes de repassar qualquer notícia, verifique sempre no *Verify*.",
        "🌐 *Acesse:* " + os.getenv("PUBLIC_FRONTEND_URL", "https://verifybr.vercel.app")
    ])

    return "\n".join(msg_lines)


MEDIA_TYPES = {
    "audio", "voice", "ptt", "audio/ogg", "audio/mpeg", "audio/mp3",
    "audio/wav", "audio/x-wav", "audio/mp4", "audio/webm",
    "image", "image/jpeg", "image/png", "image/webp", "image/gif",
    "video", "video/mp4", "video/webm", "video/quicktime",
}


async def analyze_media(
    message: str, media_url: str, media_type: str, *, data: bytes | None = None,
) -> Dict[str, Any]:
    media_type = media_type.split(";")[0].strip().lower()
    if media_type not in MEDIA_TYPES:
        raise HTTPException(415, "Tipo de mídia não suportado.")
    if data is None:
        data = await download_media(media_url, media_type)
    declared = media_type if "/" in media_type else ""
    media = await validate_media(data, "whatsapp-media", declared)
    expected_kind = {"voice": "audio", "ptt": "audio"}.get(
        media_type, media_type.split("/")[0]
    )
    if media.kind != expected_kind:
        raise HTTPException(415, "O conteúdo da mídia não corresponde ao tipo informado.")
    report = await analyze_validated_media(media)
    report["caption"] = message
    report["content_media_type"] = media.kind
    return report


async def save_anonymous_history(
    sender: str, content_type: str, query_preview: str, report: Dict[str, Any],
    reply_text: str, had_audio_reply: bool,
) -> None:
    """Legacy name: optional pseudonymous history, NOT anonymous data."""
    if (not sender or os.getenv("WHATSAPP_HISTORY_ENABLED", "false").lower() != "true"
            or len(os.getenv("WHATSAPP_HASH_SECRET", "")) < 32):
        return
    try:
        async with AsyncSessionLocal() as db:
            db.add(WhatsAppConversation(
                sender_hash=_hash_sender(sender),
                content_type=content_type,
                query_preview=(query_preview or "")[:200],
                verdict_label=report.get("verdict"),
                verdict_score=report.get("score"),
                reply_text=(reply_text or "")[:2000],
                had_audio_reply=had_audio_reply,
            ))
            await db.commit()
    except Exception:
        # DB exceptions can contain SQL parameters, including private messages.
        logging.getLogger(__name__).warning("Não foi possível salvar o histórico de WhatsApp.")


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, want_voice_reply: bool = False):
    """Authenticate incoming events and return a reply; does not send messages."""
    authenticate_webhook(request)
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(400, "JSON inválido.") from exc
    incoming = parse_message(body)
    if incoming is None:
        return {"status": "ignored", "reply": ""}
    if not incoming.base64_data and not incoming.media_url and len(incoming.text) < 10:
        return {
            "status": "ignored",
            "reply": "Envie uma mensagem com pelo menos 10 caracteres ou uma mídia para análise.",
        }
    if not receipts.claim(incoming.receipt_key):
        return {"status": "duplicate", "reply": ""}
    try:
        if incoming.base64_data or incoming.media_url:
            data = decode_media(incoming.base64_data) if incoming.base64_data else None
            with transcription_scope(webhook_transcription_scope(incoming.receipt_key)):
                report = await analyze_media(
                    incoming.text, incoming.media_url, incoming.media_type or "audio", data=data,
                )
        else:
            result = await run_pipeline(text=incoming.text)
            report = result.get("report", {})
        if has_pending_transcription(report):
            # Same authenticated receipt may now resume GET polling. Do not mark
            # a pending transcript as a completed message, persist it or run TTS.
            receipts.release(incoming.receipt_key)
            return {"status": "pending", "verdict": report.get("verdict"), "score": report.get("score"),
                    "reply": "A transcrição ainda está pendente. Isso não indica voz falsa nem ausência de fala. "
                             "Não há atualização automática; o mesmo evento pode ser consultado novamente."}
        reply = format_whatsapp_response(report, incoming.text[:60])
        audio_reply = None
        if want_voice_reply or incoming.want_voice_reply:
            tts = await get_ai_voice_speech(reply[:1200])
            if tts.get("available"):
                audio_reply = {"audio_data": tts["audio_data"], "mime_type": tts["mime_type"]}
        await save_anonymous_history(
            incoming.sender, report.get("content_media_type", "text"), incoming.text[:60],
            report, reply, bool(audio_reply),
        )
        response = {
            "status": "success", "verdict": report.get("verdict"),
            "score": report.get("score"), "reply": reply,
        }
        if audio_reply:
            response["audio_reply"] = audio_reply
        return response
    except BaseException:
        # Failed and cancelled attempts may be retried, not suppressed as completed.
        receipts.release(incoming.receipt_key)
        raise


@router.post("/whatsapp/simulate")
async def simulate_whatsapp_check(req: WhatsAppMessageRequest, request: Request,
                                  user: Optional[User] = Depends(get_optional_user)):
    """Public, rate-limited demo. Never saves simulated phone numbers/history."""
    if req.media_url:
        with transcription_scope(request_transcription_scope(request, user)):
            report = await analyze_media(req.message, req.media_url, req.media_type or "audio")
    else:
        result = await run_pipeline(text=req.message)
        report = result.get("report", {})
    reply = format_whatsapp_response(report, req.message[:60])
    audio_reply = None
    if req.want_voice_reply:
        tts = await get_ai_voice_speech(reply[:1200])
        if tts.get("available"):
            audio_reply = {"audio_data": tts["audio_data"], "mime_type": tts["mime_type"]}
    return {
        "report": report, "whatsapp_reply": reply,
        "whatsapp_response": reply, "audio_reply": audio_reply,
    }
