from fastapi import APIRouter, UploadFile, File, Form, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
from datetime import datetime, timezone

from app.core.auth import get_optional_user, verify_limit
from app.core.database import get_db
from app.models.user import User
from app.models.history import Verification, AnalysisMetrics, ContentType
from app.services.media_validation import read_media
from app.services.media_analysis import analyze_media
from app.services.pdf_snapshot import attach_pdf_snapshot
from app.services.extracted_text_review import attach_text_review
from app.services.transcription_scope import request_transcription_scope, transcription_scope

router = APIRouter()


@router.post("/upload")
async def analyze_upload(request: Request, file: UploadFile = File(...), user: User | None = Depends(get_optional_user),
                         db: AsyncSession = Depends(get_db), review_text: bool = Form(False)):
    media = await read_media(file)
    await verify_limit(user, db, "MEDIA")
    # Legacy cache has unversioned decisions and filenames belonging to other users.
    # Do not reuse it until a versioned, privacy-safe cache is implemented.
    with transcription_scope(request_transcription_scope(request, user)):
        analysis = await analyze_media(media, review_first=review_text)
    report = {**analysis, "filename": media.filename,
              "file_hash_sha256": hashlib.sha256(media.data).hexdigest(),
              "analyzed_at": datetime.now(timezone.utc).isoformat()}
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
    signed = attach_pdf_snapshot(report, user)
    return attach_text_review(signed, user) if review_text else signed
