import os
import httpx
from app.models.schemas import FactCheckResult

FACT_CHECK_BASE = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


async def query_fact_check_api(query: str) -> list[FactCheckResult]:
    """
    Query the Google Fact Check Explorer API.
    Free API – just needs an API key from Google Cloud Console.
    """
    api_key = os.getenv("GOOGLE_FACT_CHECK_KEY", "")
    if not api_key:
        return []

    params = {
        "query": query[:200],
        "languageCode": "pt-BR",
        "key": api_key,
        "pageSize": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(FACT_CHECK_BASE, params=params)
            data = resp.json()
    except Exception:
        return []

    results: list[FactCheckResult] = []
    for claim in data.get("claims", []):
        for review in claim.get("claimReview", []):
            results.append(
                FactCheckResult(
                    claim_text=claim.get("text", "")[:300],
                    rating=review.get("textualRating", "N/D"),
                    publisher=review.get("publisher", {}).get("name", "Desconhecido"),
                    url=review.get("url"),
                )
            )
    return results[:5]
