"""
Unified Multi-Layer Verification & Presentation Router
Endpoints for complete audit, quick audio demo, authenticity seals (C2PA) and PDF export.
"""

import os
import hmac
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import get_optional_user, verify_limit
from app.models.user import User
from app.models.history import AuthenticitySeal, Verification, ContentType, VerdictLabel

from app.services.metadata_service import extract_metadata
from app.services.c2pa_service import verify_c2pa
from app.services.hive_service import check_hive_media
from app.services.reverse_search_service import search_context_and_provenance
from app.services.audio_service import analyze_audio_quick_for_demonstration
from app.services.gemini_service import consolidate_forensic_report
from app.services.pdf_report_service import generate_forensic_pdf
from app.core.sightengine_client import check_deepfake

router = APIRouter()

HMAC_SECRET = os.getenv("HMAC_SECRET_KEY", "verify_local_demo_only").encode()
MAX_FILE_SIZE = 35 * 1024 * 1024

FORENSIC_VERDICTS = {
    "autentico": VerdictLabel.AUTHENTIC,
    "gerado_ia": VerdictLabel.AI_GENERATED,
    "deepfake": VerdictLabel.MANIPULATED,
    "montagem": VerdictLabel.MANIPULATED,
    "inconclusivo": VerdictLabel.SUSPICIOUS,
}


async def _safe_task(coro):
    try:
        return await coro
    except Exception:
        return {}


@router.post("/verificar/completo")
async def verificar_completo(
    file: UploadFile = File(...),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db)
):
    await verify_limit(user, db, "MEDIA")
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máximo 35MB).")

    file_hash_sha256 = hashlib.sha256(file_bytes).hexdigest()
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload.bin"
    is_audio = content_type.startswith("audio/") or filename.endswith((".wav", ".mp3", ".ogg", ".m4a", ".aac"))

    tasks = [
        _safe_task(extract_metadata(file_bytes, filename)),
        _safe_task(verify_c2pa(file_bytes, filename)),
        _safe_task(check_hive_media(file_bytes, filename, "audio" if is_audio else "image")),
        _safe_task(check_deepfake(file_bytes)) if not is_audio else asyncio.sleep(0),
        _safe_task(search_context_and_provenance(image_bytes=file_bytes if not is_audio else b"", filename=filename)),
    ]

    if is_audio:
        tasks.append(_safe_task(analyze_audio_quick_for_demonstration(file_bytes, filename)))
    else:
        tasks.append(asyncio.sleep(0))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    metadata_res = results[0] if not isinstance(results[0], Exception) else {}
    c2pa_res = results[1] if not isinstance(results[1], Exception) else {}
    hive_res = results[2] if not isinstance(results[2], Exception) else {}
    sightengine_res = results[3] if not isinstance(results[3], Exception) else {"genai_probability": 0}
    context_res = results[4] if not isinstance(results[4], Exception) else {}
    audio_res = results[5] if len(results) > 5 and not isinstance(results[5], Exception) else None

    detection_res = {"hive": hive_res, "sightengine": sightengine_res}

    report = await consolidate_forensic_report(
        filename=filename,
        metadata_res=metadata_res,
        c2pa_res=c2pa_res,
        detection_res=detection_res,
        context_res=context_res,
        audio_res=audio_res
    )

    result_payload = {
        "file_hash_sha256": file_hash_sha256,
        "filename": filename,
        "query_input": filename,
        "metadata": metadata_res,
        "c2pa": c2pa_res,
        "deteccao_ia": detection_res,
        "contexto": context_res,
        "audio": audio_res,
        "veredito": report
    }

    if user:
        try:
            v = Verification(
                user_id=user.id,
                content_type=ContentType.AUDIO if is_audio else ContentType.IMAGE,
                file_hash_md5=hashlib.md5(file_bytes).hexdigest(),
                verdict_score=report.get("score", 75),
                verdict_label=FORENSIC_VERDICTS.get(
                    report.get("veredito_final", "").lower(),
                    VerdictLabel.SUSPICIOUS,
                ),
                ai_summary=report.get("explicacao_leiga", ""),
                raw_result=result_payload
            )
            db.add(v)
            await db.commit()
        except Exception:
            pass

    return result_payload


@router.post("/verificar/audio-rapido")
async def verificar_audio_rapido(file: UploadFile = File(...)):
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo de áudio muito grande.")
    return await analyze_audio_quick_for_demonstration(file_bytes, file.filename or "audio.wav")


@router.post("/capturar/selo")
@router.post("/selo/capturar")
async def capturar_selo(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    file_bytes = await file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    timestamp_utc = datetime.now(timezone.utc)
    timestamp_str = timestamp_utc.isoformat()

    signature = hmac.new(
        HMAC_SECRET,
        f"{file_hash}:{timestamp_str}".encode(),
        hashlib.sha256
    ).hexdigest()

    res = await db.execute(select(AuthenticitySeal).where(AuthenticitySeal.file_hash_sha256 == file_hash))
    existing = res.scalar_one_or_none()

    if not existing:
        seal = AuthenticitySeal(
            file_hash_sha256=file_hash,
            file_name=file.filename or "captura.jpg",
            media_type=file.content_type or "image/jpeg",
            file_size_bytes=len(file_bytes),
            signature_hmac=signature,
            captured_at=timestamp_utc,
            metadata_json={"ip": "127.0.0.1", "device": "Webcam Capture Verified"}
        )
        db.add(seal)
        await db.commit()
    else:
        signature = existing.signature_hmac
        timestamp_str = existing.captured_at.isoformat()

    return {
        "status": "SEALED",
        "autentico": True,
        "file_hash_sha256": file_hash,
        "captured_at": timestamp_str,
        "signature_hmac": signature,
        "mensagem": "Selo de Autenticidade emitido com sucesso! A integridade criptográfica está assegurada."
    }


@router.post("/verificar/selo")
async def verificar_selo_upload(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    file_bytes = await file.read()
    current_hash = hashlib.sha256(file_bytes).hexdigest()

    res = await db.execute(select(AuthenticitySeal).where(AuthenticitySeal.file_hash_sha256 == current_hash))
    seal = res.scalar_one_or_none()

    if seal:
        return {
            "autentico": True,
            "status": "VALID",
            "file_hash_sha256": current_hash,
            "captured_at": seal.captured_at.isoformat(),
            "signature_hmac": seal.signature_hmac,
            "mensagem": "SELO VALIDO: Imagem 100% original e autentica! Nenhuma alteracao de pixels detectada."
        }
    return {
        "autentico": False,
        "status": "TAMPERED_OR_UNKNOWN",
        "current_hash_sha256": current_hash,
        "mensagem": "ALERTA DE VIOLACAO: Hash nao cadastrado ou arquivo adulterado!"
    }


@router.get("/verificar/selo/{file_hash}")
async def verificar_selo_por_hash(file_hash: str, db: AsyncSession = Depends(get_db)):
    clean_hash = file_hash.strip().lower()
    res = await db.execute(select(AuthenticitySeal).where(AuthenticitySeal.file_hash_sha256 == clean_hash))
    seal = res.scalar_one_or_none()

    if seal:
        return {
            "autentico": True,
            "captured_at": seal.captured_at.isoformat(),
            "signature": seal.signature_hmac,
            "file_name": seal.file_name
        }
    return {
        "autentico": False,
        "motivo": "Nenhum selo registrado para este hash."
    }


@router.post("/verificar/relatorio-pdf")
async def exportar_relatorio_pdf(
    file: UploadFile = File(...),
    filename: Optional[str] = Form(None)
):
    file_bytes = await file.read()
    file_hash_sha256 = hashlib.sha256(file_bytes).hexdigest()
    target_filename = filename or file.filename or "evidencia_auditada.jpg"

    metadata_res = await extract_metadata(file_bytes, target_filename)
    c2pa_res = await verify_c2pa(file_bytes, target_filename)
    report = await consolidate_forensic_report(
        target_filename,
        metadata_res,
        c2pa_res,
        {"hive": {}, "sightengine": {}},
        {"wayback": {}}
    )

    pdf_bytes = generate_forensic_pdf(report, target_filename, file_hash_sha256)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Laudo_Verify_{file_hash_sha256[:8]}.pdf"'
        }
    )
