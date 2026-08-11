from fastapi import APIRouter, Depends, HTTPException
import httpx
from bs4 import BeautifulSoup
import re

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import UrlRequest
from app.core.pipeline import run_pipeline
from app.core.security import sanitize
from app.core.auth import get_current_user, verify_limit
from app.core.database import get_db
from app.models.user import User
from app.models.history import Verification, AnalysisMetrics, ContentType

router = APIRouter()
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AntigravityBot/1.0)"}


async def fetch_page_text(url: str) -> dict:
    """Robust scraper for Antigravity Core."""
    async with httpx.AsyncClient(timeout=15, headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Metadata
    meta = {
        "title": soup.title.string if soup.title else "",
        "description": "",
    }
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if desc_tag:
        meta["description"] = desc_tag.get("content", "")

    # Cleanup
    for tag in soup(["script", "style", "nav", "footer", "aside", "header", "form"]):
        tag.decompose()
        
    # Main content
    main = soup.find("main") or soup.find("article") or soup.body
    text = re.sub(r"\s+", " ", main.get_text(separator=" ", strip=True)).strip()
    
    return {
        "text": text[:5000],
        "meta": meta
    }


@router.post("/check-url")
async def check_url(
    body: UrlRequest,
    user: User         = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    await verify_limit(user, db, "TEXTUAL")
    
    url = sanitize(body.url.strip())
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        scraped = await fetch_page_text(url)
        page_text = scraped["text"]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Acesso negado ou erro na URL: {str(exc)[:100]}")

    if len(page_text) < 50:
        raise HTTPException(status_code=422, detail="Conteúdo insuficiente para auditoria.")

    result = await run_pipeline(text=page_text, url=url)
    ai = result["report"]
    ai["fact_checks"] = [fc.model_dump() for fc in result.get("fact_checks", [])]
    metrics = result["metrics"]

    v = Verification(
        user_id=user.id,
        content_type=ContentType.TEXT,
        source_url=url,
        verdict_score=ai["score"],
        verdict_label=ai["verdict"],
        ai_summary=ai["summary"],
        raw_result=ai
    )
    db.add(v)
    await db.flush()

    m = AnalysisMetrics(
        verification_id=v.id,
        text_ai_probability=metrics["text_ai_probability"],
        earliest_known_date=metrics["earliest_known_date"]
    )
    db.add(m)
    
    await db.commit()
    return ai
