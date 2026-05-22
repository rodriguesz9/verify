from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.core.gemini_analyzer import generate_final_report
from app.core.sightengine_client import check_deepfake
from app.core.huggingface_client import check_ai_image_hf
from app.core.auth import get_current_user, verify_limit
from app.core.database import get_db
from app.models.schemas import AnalysisResponse
from app.models.user import User
from app.models.history import VerificationLog, QueryType

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "video/mp4", "video/webm",
    "audio/mpeg", "audio/wav"
}
MAX_SIZE = 15 * 1024 * 1024


@router.post("/upload", response_model=AnalysisResponse)
async def analyze_upload(
    file: UploadFile      = File(...),
    user: User            = Depends(get_current_user),
    db:   AsyncSession    = Depends(get_db),
):
    await verify_limit(user, db, "MEDIA")

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo muito grande.")

    is_image = file.content_type.startswith("image/")
    q_type = QueryType.VIDEO if "video" in file.content_type else QueryType.AUDIO if "audio" in file.content_type else QueryType.IMAGE

    # Parallel Forensic Collection
    tasks = []
    if is_image:
        tasks.append(asyncio.create_task(check_deepfake(data)))
        tasks.append(asyncio.create_task(check_ai_image_hf(data)))
    
    # We can still use Gemini for all media types as the chief perito
    # Note: we pass dummy text or description if it was a file
    
    forensics = {}
    if tasks:
        results = await asyncio.gather(*tasks)
        forensics["sightengine"] = results[0]
        forensics["huggingface"]  = results[1]

    # Final Orchestration
    # For media, we can also extract text from Gemini's internal vision if we used it,
    # but for now we consolidate the forensic results.
    ai = await generate_final_report(f"Arquivo enviado: {file.filename}", forensics)

    result = AnalysisResponse(
        score              =int(ai.get("score", 50)),
        semantic_score     =int(ai.get("semantic_score", 50)),
        domain_score       =70,
        sensationalism     =int(ai.get("sensationalism", 50)),
        verdict            =ai.get("verdict", "SUSPEITO"),
        summary            =ai.get("summary", ""),
        red_flags          =ai.get("red_flags", []),
        positive_signals   =ai.get("positive_signals", []),
        logical_fallacies  =ai.get("logical_fallacies", []),
        emotional_triggers =bool(ai.get("emotional_triggers", False)),
        fact_checks        =[],
        domain_note        ="Análise forense de mídia concluída.",
        recommended_sources=ai.get("recommended_sources", []),
        hive_result        =forensics.get("sightengine"), # Map to UI field
    )

    log = VerificationLog(
        user_id    =user.id,
        query_type =q_type,
        query_input=file.filename[:500],
        result     =result.model_dump(),
        score      =result.score,
        verdict    =result.verdict,
        summary    =result.summary,
    )
    db.add(log)
    await db.commit()
    return result
