from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import asyncio
import hashlib

from app.core.gemini_analyzer import generate_final_report
from app.core.sightengine_client import check_deepfake
from app.core.huggingface_client import check_ai_image_hf
from app.core.auth import get_current_user, verify_limit
from app.core.database import get_db
from app.models.schemas import AnalysisResponse
from app.models.user import User
from app.models.history import Verification, AnalysisMetrics, CacheRegistry, ContentType, VerdictLabel

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "video/mp4", "audio/mpeg"}
MAX_SIZE = 15 * 1024 * 1024


@router.post("/upload")
async def analyze_upload(
    file: UploadFile      = File(...),
    user: User            = Depends(get_current_user),
    db:   AsyncSession    = Depends(get_db),
):
    await verify_limit(user, db, "MEDIA")

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo muito grande.")

    # 1. Cache Check
    file_hash = hashlib.md5(data).hexdigest()
    cache_res = await db.execute(select(CacheRegistry).where(CacheRegistry.file_hash_md5 == file_hash))
    cache_entry = cache_res.scalar_one_or_none()
    
    if cache_entry and cache_entry.expires_at > datetime.now():
        # Pull cached verification
        v_res = await db.execute(select(Verification).where(Verification.id == cache_entry.cached_verdict_id))
        cached_v = v_res.scalar_one_or_none()
        if cached_v:
            return cached_v.raw_result

    # 2. Analysis
    is_image = file.content_type.startswith("image/")
    c_type   = ContentType.VIDEO if "video" in file.content_type else ContentType.AUDIO if "audio" in file.content_type else ContentType.IMAGE

    forensics = {}
    if is_image:
        df_task = asyncio.create_task(check_deepfake(data))
        hf_task = asyncio.create_task(check_ai_image_hf(data))
        await asyncio.gather(df_task, hf_task)
        forensics["sightengine"] = df_task.result()
        forensics["huggingface"]  = hf_task.result()

    ai = await generate_final_report(f"Auditoria: {file.filename}", {"forensics": forensics})

    # 3. Save Verification
    v = Verification(
        user_id=user.id,
        content_type=c_type,
        file_hash_md5=file_hash,
        verdict_score=int(ai["score"]),
        verdict_label=ai["verdict"], # VerdictLabel enum matches AI string if prompt is good
        ai_summary=ai["summary"],
        raw_result=ai
    )
    db.add(v)
    await db.flush() # Get ID

    # 4. Save Metrics
    m = AnalysisMetrics(
        verification_id=v.id,
        sightengine_ai_score=forensics.get("sightengine", {}).get("genai_probability"),
        sightengine_deepfake_score=forensics.get("sightengine", {}).get("deepfake_probability"),
        huggingface_model_score=forensics.get("huggingface", {}).get("ai_probability")
    )
    db.add(m)

    # 5. Update Cache
    if not cache_entry:
        cache_entry = CacheRegistry(
            file_hash_md5=file_hash,
            cached_verdict_id=v.id,
            expires_at=datetime.now() + timedelta(days=7)
        )
        db.add(cache_entry)
    else:
        cache_entry.cached_verdict_id = v.id
        cache_entry.expires_at = datetime.now() + timedelta(days=7)

    await db.commit()
    return ai
