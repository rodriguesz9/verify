from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import asyncio
import hashlib

from app.core.gemini_analyzer import generate_final_report
from app.core.sightengine_client import check_deepfake
from app.core.huggingface_client import check_ai_image_hf
from app.core.auth import get_optional_user, get_current_user, verify_limit
from app.core.database import get_db
from app.models.user import User
from app.models.history import Verification, AnalysisMetrics, CacheRegistry, ContentType

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "video/mp4", "video/quicktime",
    "audio/mpeg", "audio/ogg", "audio/wav", "audio/mp4", "audio/x-m4a", "audio/m4a", "audio/aac", "audio/webm"
}
MAX_SIZE = 25 * 1024 * 1024


def _has_ai_orchestration_failure(result: dict) -> bool:
    red_flags = result.get("red_flags", [])
    return any("Falha na orquestração" in flag for flag in red_flags)


@router.post("/upload")
async def analyze_upload(
    file: UploadFile = File(...),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_limit(user, db, "MEDIA")

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo muito grande. Máximo permitido: 25MB.")

    # 1. Cache Check
    file_hash = hashlib.md5(data).hexdigest()
    cache_res = await db.execute(select(CacheRegistry).where(CacheRegistry.file_hash_md5 == file_hash))
    cache_entry = cache_res.scalar_one_or_none()
    if cache_entry and cache_entry.expires_at > datetime.now(timezone.utc):
        v_res = await db.execute(select(Verification).where(Verification.id == cache_entry.cached_verdict_id))
        cached_v = v_res.scalar_one_or_none()
        if cached_v:
            if _has_ai_orchestration_failure(cached_v.raw_result):
                await db.delete(cache_entry)
                await db.flush()
                cache_entry = None
            else:
                return cached_v.raw_result

    # 2. Analysis
    content_type_str = file.content_type or "application/octet-stream"
    is_image = content_type_str.startswith("image/")
    is_audio = content_type_str.startswith("audio/") or file.filename.endswith((".mp3", ".ogg", ".wav", ".m4a", ".aac", ".opus"))
    
    c_type = (
        ContentType.AUDIO
        if is_audio
        else ContentType.VIDEO
        if "video" in content_type_str
        else ContentType.IMAGE
    )

    forensics = {}
    if is_audio:
        from app.core.audio_checker import transcribe_and_extract_audio
        from app.core.pipeline import run_pipeline
        
        transcribed_text = await transcribe_and_extract_audio(data, content_type_str)
        if not transcribed_text:
            transcribed_text = f"Áudio recebido para análise: {file.filename}"
            
        pipeline_res = await run_pipeline(text=transcribed_text)
        ai = pipeline_res.get("report", {})
        ai["transcription"] = transcribed_text
        ai["content_type"] = "audio"
    elif is_image:
        df_task = asyncio.create_task(check_deepfake(data))
        hf_task = asyncio.create_task(check_ai_image_hf(data))
        await asyncio.gather(df_task, hf_task)
        forensics["sightengine"] = df_task.result()
        forensics["huggingface"] = hf_task.result()
        ai = await generate_final_report(f"Auditoria de Imagem: {file.filename}", {"forensics": forensics})
    else:
        ai = await generate_final_report(f"Auditoria de Mídia: {file.filename}", {"forensics": forensics})
    
    if _has_ai_orchestration_failure(ai):
        raise HTTPException(status_code=502, detail="Falha na analise de IA")

    ai["query_input"] = file.filename or "Arquivo enviado"

    # 3. Save Verification (if user logged in)
    if user:
        v = Verification(
            user_id=user.id,
            content_type=c_type,
            file_hash_md5=file_hash,
            verdict_score=int(ai["score"]),
            verdict_label=ai["verdict"],
            ai_summary=ai["summary"],
            raw_result=ai,
        )
        db.add(v)
        await db.flush()

        m = AnalysisMetrics(
            verification_id=v.id,
            sightengine_ai_score=forensics.get("sightengine", {}).get("genai_probability"),
            sightengine_deepfake_score=forensics.get("sightengine", {}).get("deepfake_probability"),
            huggingface_model_score=forensics.get("huggingface", {}).get("ai_probability"),
        )
        db.add(m)

        if not cache_entry:
            cache_entry = CacheRegistry(
                file_hash_md5=file_hash,
                cached_verdict_id=v.id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
            db.add(cache_entry)
        else:
            cache_entry.cached_verdict_id = v.id
            cache_entry.expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        await db.commit()

    return ai
