"""Authenticated webhook parsing and bounded, per-process replay protection."""

import base64
import binascii
import hashlib
import hmac
import os
import time
from collections import OrderedDict
from dataclasses import dataclass

from fastapi import HTTPException, Request

MAX_MEDIA_BYTES = 25 * 1024 * 1024


def authenticate_webhook(request: Request) -> None:
    if os.getenv("WHATSAPP_BOT_ENABLED", "false").lower() != "true":
        raise HTTPException(503, "O webhook de WhatsApp está desativado.")
    secret = os.getenv("WHATSAPP_WEBHOOK_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(503, "Autenticação do webhook não configurada.")
    supplied = request.headers.get("x-verify-webhook-secret", "")
    if not hmac.compare_digest(supplied.encode(), secret.encode()):
        raise HTTPException(401, "Autenticação do webhook inválida.")


def _string(value, label: str, limit: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) or len(value) > limit:
        raise HTTPException(422, f"Campo {label} inválido ou muito longo.")
    return value


def decode_media(encoded: str) -> bytes:
    if len(encoded) > 4 * ((MAX_MEDIA_BYTES + 2) // 3) + 200:
        raise HTTPException(413, "Mídia muito grande (máx 25MB).")
    if encoded.startswith("data:"):
        prefix, separator, encoded = encoded.partition(",")
        if not separator or not prefix.endswith(";base64"):
            raise HTTPException(422, "Mídia base64 inválida.")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(422, "Mídia base64 inválida.") from exc
    if not data:
        raise HTTPException(422, "Mídia vazia.")
    if len(data) > MAX_MEDIA_BYTES:
        raise HTTPException(413, "Mídia muito grande (máx 25MB).")
    return data


@dataclass
class IncomingMessage:
    text: str = ""
    sender: str = ""
    media_url: str = ""
    media_type: str = ""
    base64_data: str = ""
    receipt_key: str = ""
    want_voice_reply: bool = False


def parse_message(body: dict) -> IncomingMessage | None:
    if not isinstance(body, dict):
        raise HTTPException(422, "O webhook deve conter um objeto JSON.")
    event = _string(body.get("event"), "event", 128).lower().replace("_", ".")
    if event and event != "messages.upsert":
        return None
    data = body.get("data", body)
    if not isinstance(data, dict):
        raise HTTPException(422, "Formato de evento não suportado.")
    key = data.get("key", {})
    if not isinstance(key, dict):
        raise HTTPException(422, "Chave de mensagem inválida.")
    from_me = key.get("fromMe", body.get("fromMe", False))
    if not isinstance(from_me, bool):
        raise HTTPException(422, "Campo fromMe inválido.")
    if from_me:
        return None
    raw = data.get("message", body.get("message", {}))
    if not isinstance(raw, (dict, str)):
        raise HTTPException(422, "Mensagem inválida.")
    message = raw if isinstance(raw, dict) else {}
    text = raw if isinstance(raw, str) else message.get("conversation") or message.get("text", "")
    extended = message.get("extendedTextMessage", {})
    if isinstance(extended, dict):
        text = text or extended.get("text", "")
    text = text or data.get("text", "") or body.get("text", "")
    media_obj = {}
    kind = ""
    for field, candidate in (
        ("audioMessage", "audio"), ("pttMessage", "audio"),
        ("imageMessage", "image"), ("videoMessage", "video"),
    ):
        if field in message:
            media_obj = message[field]
            if not isinstance(media_obj, dict):
                raise HTTPException(422, "Mensagem de mídia inválida.")
            kind = candidate
            text = text or media_obj.get("caption", "")
            break
    sender = key.get("remoteJid") or data.get("remoteJid") or body.get("from") or body.get("sender", "")
    sender = _string(sender, "sender", 256)
    media_url = _string(
        body.get("media_url") or data.get("media_url") or media_obj.get("url"),
        "media_url", 4096,
    )
    media_type = _string(
        body.get("media_type") or data.get("media_type") or media_obj.get("mimetype") or kind,
        "media_type", 100,
    )
    encoded = _string(
        data.get("base64") or media_obj.get("base64") or body.get("base64"),
        "base64", 4 * ((MAX_MEDIA_BYTES + 2) // 3) + 200,
    )
    want_voice = body.get("want_voice_reply", False)
    if not isinstance(want_voice, bool):
        raise HTTPException(422, "Campo want_voice_reply inválido.")
    message_id = _string(key.get("id") or body.get("message_id"), "message_id", 256)
    instance = _string(body.get("instance"), "instance", 256)
    # Scope IDs by integration and sender. Never retain phone numbers in memory keys.
    receipt = hashlib.sha256(
        (instance + "\0" + sender + "\0" + message_id).encode()
    ).hexdigest() if message_id else ""
    return IncomingMessage(
        _string(text, "message", 5000).strip(), sender, media_url, media_type,
        encoded, receipt, want_voice,
    )


class ReceiptGuard:
    """Suppress duplicate/in-flight events for 10 minutes in ONE worker."""
    def __init__(self, ttl: float = 600.0, capacity: int = 5000):
        self.ttl = ttl
        self.capacity = capacity
        self._items: OrderedDict[str, float] = OrderedDict()

    def claim(self, key: str) -> bool:
        if not key:
            return True
        now = time.monotonic()
        while self._items and next(iter(self._items.values())) <= now:
            self._items.popitem(last=False)
        if key in self._items:
            return False
        if len(self._items) >= self.capacity:
            raise HTTPException(503, "Fila de mensagens ocupada. Tente novamente mais tarde.")
        self._items[key] = now + self.ttl
        return True

    def release(self, key: str) -> None:
        self._items.pop(key, None)


receipts = ReceiptGuard()
