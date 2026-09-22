from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import os
from app.core.pipeline import run_pipeline
from app.core.audio_checker import transcribe_and_extract_audio

router = APIRouter()

class WhatsAppMessageRequest(BaseModel):
    message: str
    from_number: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None # text, audio, image

def format_whatsapp_response(report: Dict[str, Any], query_preview: str = "") -> str:
    verdict = report.get("verdict", "Suspicious")
    score = report.get("score", 50)
    summary = report.get("summary", "")
    plain_explanation = report.get("plain_explanation", "")
    elderly_tip = report.get("elderly_tip", "")
    
    # Verdict visual badges
    if verdict == "Authentic":
        badge = "✅ *VERDADEIRO / NOTÍCIA REAL*"
        score_text = f"🟢 Confiança: {score}%"
    elif verdict == "Scam":
        badge = "🚨 *CUIDADO: ALERTA DE GOLPE / FRAUDE*"
        score_text = f"🔴 Risco: ALTO (Score {score}%)"
    elif verdict in ["Manipulated", "AI_Generated"]:
        badge = "❌ *CONTEÚDO FALSO / MANIPULADO*"
        score_text = f"🔴 Risco de engano: ALTO (Score {score}%)"
    elif verdict == "Out_Of_Context":
        badge = "🔍 *FORA DE CONTEXTO / HISTÓRIA ANTIGA*"
        score_text = f"🟠 Atenção: {score}%"
    else:
        badge = "⚠️ *SUSPEITO / NÃO CONFIRMADO*"
        score_text = f"🟡 Cautela: {score}%"

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
        "🌐 *Acesse:* https://verify.vercel.app"
    ])

    return "\n".join(msg_lines)

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """
    General Webhook for WhatsApp integrations (Evolution API, Z-API, Baileys, etc.).
    Receives incoming WhatsApp message, runs fact check, and returns formatted message.
    """
    body = await request.json()
    
    # Extract message from various payload structures
    text = ""
    sender = body.get("from") or body.get("remoteJid") or body.get("sender") or ""
    
    # Check if payload is direct or from an instance provider
    if "message" in body:
        if isinstance(body["message"], str):
            text = body["message"]
        elif isinstance(body["message"], dict):
            text = body["message"].get("conversation") or body["message"].get("text") or ""
    elif "data" in body and isinstance(body["data"], dict):
        text = body["data"].get("message", {}).get("conversation") or body["data"].get("text", "")
    elif "text" in body:
        text = str(body["text"])

    if not text.strip():
        return {
            "status": "ignored",
            "reply": "Olá! Envie um texto, notícia ou link para que o *Verify* verifique se é verdadeiro ou falso. 🔍"
        }

    # Run check
    pipeline_result = await run_pipeline(text=text)
    report = pipeline_result.get("report", {})
    reply_text = format_whatsapp_response(report, text[:60])
    
    return {
        "status": "success",
        "verdict": report.get("verdict"),
        "score": report.get("score"),
        "reply": reply_text
    }

@router.post("/whatsapp/simulate")
async def simulate_whatsapp_check(req: WhatsAppMessageRequest):
    """
    Simulates sending a message to WhatsApp bot and getting the exact reply.
    """
    pipeline_result = await run_pipeline(text=req.message)
    report = pipeline_result.get("report", {})
    formatted_reply = format_whatsapp_response(report, req.message[:60])
    
    return {
        "report": report,
        "whatsapp_reply": formatted_reply,
        "whatsapp_response": formatted_reply
    }
