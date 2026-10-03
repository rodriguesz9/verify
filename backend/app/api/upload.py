from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib

from app.core.auth import get_optional_user, verify_limit
from app.core.database import get_db
from app.models.user import User
from app.models.history import Verification, AnalysisMetrics, ContentType
from app.services.media_validation import read_media
from app.services.media_analysis import analyze_media

router = APIRouter()


@router.post("/upload")
async def analyze_upload(file: UploadFile = File(...), user: User | None = Depends(get_optional_user),
                         db: AsyncSession = Depends(get_db)):
    media = await read_media(file)
    await verify_limit(user, db, "MEDIA")
    # Legacy cache has unversioned decisions and filenames belonging to other users.
    # Do not reuse it until a versioned, privacy-safe cache is implemented.
    report = await analyze_media(media)
    if user:
        verification = Verification(user_id=user.id, content_type=ContentType[media.kind.upper()],
            file_hash_md5=hashlib.md5(media.data).hexdigest(), verdict_score=report["score"],
            verdict_label=report["verdict"], ai_summary=report["summary"], raw_result=report)
        db.add(verification)
        await db.flush()
        forensics = report.get("forensics", {})
        db.add(AnalysisMetrics(verification_id=verification.id,
            sightengine_ai_score=forensics.get("sightengine", {}).get("genai_probability"),
            sightengine_deepfake_score=forensics.get("sightengine", {}).get("deepfake_probability"),
            huggingface_model_score=forensics.get("huggingface", {}).get("ai_probability")))
        await db.commit()
    return report
