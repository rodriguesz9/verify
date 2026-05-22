from fastapi import APIRouter, Depends, HTTPException
import httpx
from bs4 import BeautifulSoup
import re

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import UrlRequest, AnalysisResponse
from app.core.pipeline import run_pipeline
from app.core.security import sanitize
from app.core.auth import get_current_user, verify_limit
from app.core.database import get_db
from app.models.user import User
from app.models.history import VerificationLog, QueryType

router = APIRouter()
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; VerifAIBot/1.0)"}


async def fetch_page_text(url: str) -> dict:
    """Robust scraper for news content."""
    async with httpx.AsyncClient(timeout=12, headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Extract metadata
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
        
    # Get main content
    main = soup.find("main") or soup.find("article") or soup.body
    text = re.sub(r"\s+", " ", main.get_text(separator=" ", strip=True)).strip()
    
    return {
        "text": text[:4000],
        "meta": meta
    }


@router.post("/check-url", response_model=AnalysisResponse)
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
        raise HTTPException(status_code=400, detail=f"Não foi possível acessar a URL: {str(exc)[:100]}")

    if len(page_text) < 50:
        raise HTTPException(status_code=422, detail="Conteúdo insuficiente para análise.")

    result = await run_pipeline(text=page_text, url=url)

    log = VerificationLog(
        user_id    =user.id,
        query_type =QueryType.URL,
        query_input=url[:500],
        result     =result.model_dump(),
        score      =result.score,
        verdict    =result.verdict,
        summary    =result.summary,
    )
    db.add(log)
    await db.commit()
    return result
