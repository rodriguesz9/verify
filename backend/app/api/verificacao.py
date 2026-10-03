"""Media audit, voice-content demo, byte-integrity registry and PDF export."""
import os
import hmac
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import get_optional_user, verify_limit
from app.models.user import User
from app.models.history import AuthenticitySeal, Verification, ContentType
from app.services.media_validation import read_media
from app.services.media_analysis import analyze_media
from app.services.audio_service import analyze_audio_quick_for_demonstration
from app.services.evidence_policy import forensic_contract
from app.services.pdf_report_service import generate_forensic_pdf

router = APIRouter()
HMAC_SECRET = os.getenv("HMAC_SECRET_KEY", "verify_local_demo_only").encode()
SEAL_LIMITATION = "Este registro comprova correspondência dos bytes, não a veracidade da cena, autoria ou origem. Não é uma credencial C2PA."


@router.post("/verificar/completo")
async def verificar_completo(file: UploadFile = File(...), user: Optional[User] = Depends(get_optional_user),
                            db: AsyncSession = Depends(get_db)):
    media = await read_media(file)
    await verify_limit(user, db, "MEDIA")
    report = await analyze_media(media)
    layers = report["forensics"]
    payload = {**report, "file_hash_sha256": hashlib.sha256(media.data).hexdigest(),
        "filename": media.filename, "metadata": layers.get("metadata", {}), "c2pa": layers.get("c2pa", {}),
        "deteccao_ia": {name: layers.get(name, {}) for name in ("hive", "sightengine", "huggingface")},
        "contexto": layers.get("context", {}), "audio": layers.get("audio"),
        "veredito": forensic_contract(report)}
    if user:
        db.add(Verification(user_id=user.id, content_type=ContentType[media.kind.upper()],
            file_hash_md5=hashlib.md5(media.data).hexdigest(), verdict_score=report["score"],
            verdict_label=report["verdict"], ai_summary=report["summary"], raw_result=payload))
        # Do not silently swallow persistence errors or report a saved history that isn't saved.
        await db.commit()
    return payload


@router.post("/verificar/audio-rapido")
async def verificar_audio_rapido(file: UploadFile = File(...)):
    media = await read_media(file, "audio")
    report = await analyze_media(media)
    transcript = report["forensics"].get("audio", {})
    return {**transcript, **report,
            "verdict": "indicios_sintetica" if report["verdict"] == "AI_Generated" else "inconclusiva",
            "short_explanation": report["summary"], "score_percent": None}


def _seal_payload(seal: AuthenticitySeal) -> dict:
    return {"autentico": False, "integridade_verificada": True, "status": "VALID",
        "file_hash_sha256": seal.file_hash_sha256, "captured_at": seal.captured_at.isoformat(),
        "signature_hmac": seal.signature_hmac,
        "mensagem": "Os bytes correspondem ao arquivo registrado no Verify.", "limitations": [SEAL_LIMITATION]}


@router.post("/capturar/selo")
@router.post("/selo/capturar")
async def capturar_selo(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    media = await read_media(file, "image")
    file_hash = hashlib.sha256(media.data).hexdigest()
    existing = (await db.execute(select(AuthenticitySeal).where(AuthenticitySeal.file_hash_sha256 == file_hash))).scalar_one_or_none()
    if not existing:
        timestamp = datetime.now(timezone.utc)
        signature = hmac.new(HMAC_SECRET, f"{file_hash}:{timestamp.isoformat()}".encode(), hashlib.sha256).hexdigest()
        existing = AuthenticitySeal(file_hash_sha256=file_hash, file_name=media.filename, media_type=media.mime_type,
            file_size_bytes=len(media.data), signature_hmac=signature, captured_at=timestamp,
            metadata_json={"origin": "unverified_upload", "registry_type": "byte_integrity_not_c2pa"})
        db.add(existing)
        await db.commit()
    return {**_seal_payload(existing), "status": "SEALED"}


@router.post("/verificar/selo")
async def verificar_selo_upload(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    media = await read_media(file)
    current_hash = hashlib.sha256(media.data).hexdigest()
    seal = (await db.execute(select(AuthenticitySeal).where(AuthenticitySeal.file_hash_sha256 == current_hash))).scalar_one_or_none()
    if seal:
        return _seal_payload(seal)
    return {"autentico": False, "integridade_verificada": False, "status": "TAMPERED_OR_UNKNOWN",
            "current_hash_sha256": current_hash, "mensagem": "Não há registro destes bytes. Isso não prova adulteração.",
            "limitations": [SEAL_LIMITATION]}


@router.get("/verificar/selo/{file_hash}")
async def verificar_selo_por_hash(file_hash: str, db: AsyncSession = Depends(get_db)):
    clean_hash = file_hash.strip().lower()
    if not re.fullmatch(r"[a-f0-9]{64}", clean_hash):
        raise HTTPException(422, "Hash SHA-256 inválido.")
    seal = (await db.execute(select(AuthenticitySeal).where(AuthenticitySeal.file_hash_sha256 == clean_hash))).scalar_one_or_none()
    if seal:
        # Hash lookup cannot establish possession/identity of the caller's file.
        return {"autentico": False, "registered": True, "captured_at": seal.captured_at.isoformat(),
                "limitations": [SEAL_LIMITATION]}
    return {"autentico": False, "registered": False, "motivo": "Nenhum registro para este hash."}


@router.post("/verificar/relatorio-pdf")
async def exportar_relatorio_pdf(file: UploadFile = File(...), filename: Optional[str] = Form(None),
                               user: Optional[User] = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    media = await read_media(file)
    await verify_limit(user, db, "MEDIA")
    report = await analyze_media(media)
    file_hash = hashlib.sha256(media.data).hexdigest()
    layers = report["forensics"]
    pdf_report = {**forensic_contract(report), "metadata": layers.get("metadata", {}),
                  "contexto": layers.get("context", {})}
    pdf_bytes = generate_forensic_pdf(pdf_report, media.filename, file_hash)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="Relatorio_Verify_{file_hash[:8]}.pdf"'})
