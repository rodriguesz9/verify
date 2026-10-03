import os

import httpx
from dotenv import load_dotenv
from app.models.schemas import FactCheckResult

load_dotenv()

FACT_CHECK_BASE = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


class FactCheckSearch(list):
    def __init__(self, items=(), status="success", reason=None):
        super().__init__(items)
        self.status, self.reason = status, reason


async def query_fact_check_api(query: str) -> list[FactCheckResult]:
    """
    Query the Google Fact Check Explorer API.
    Free API – just needs an API key from Google Cloud Console.
    """
    api_key = os.getenv("GOOGLE_FACT_CHECK_KEY", "")
    if not api_key:
        return FactCheckSearch(status="not_configured", reason="GOOGLE_FACT_CHECK_KEY não configurada.")

    params = {
        "query": query[:5000],
        "languageCode": "pt",
        "key": api_key,
        "pageSize": 10,
    }

    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            resp = await client.get(FACT_CHECK_BASE, params=params)
            if resp.status_code != 200:
                return FactCheckSearch(status="error", reason=f"Google Fact Check indisponível (HTTP {resp.status_code}).")
            data = resp.json()
            if not isinstance(data, dict) or not isinstance(data.get("claims", []), list):
                raise ValueError("Invalid response")
    except httpx.TimeoutException:
        return FactCheckSearch(status="timeout", reason="Tempo limite da consulta de checagens.")
    except Exception:
        return FactCheckSearch(status="invalid_response", reason="Resposta de checagens indisponível ou inválida.")

    results: list[FactCheckResult] = []
    for claim in data.get("claims", []):
        if not isinstance(claim, dict) or not isinstance(claim.get("text"), str) or len(claim["text"]) > 10000:
            continue
        for review in claim.get("claimReview", []) if isinstance(claim.get("claimReview", []), list) else []:
            if not isinstance(review, dict) or not isinstance(review.get("publisher"), dict):
                continue
            if any(value is not None and not isinstance(value, str) for value in (
                review.get("textualRating"), review.get("url"), review.get("reviewDate"), claim.get("claimDate"),
                review["publisher"].get("name"), review["publisher"].get("site"))):
                continue
            results.append(
                FactCheckResult(
                    claim_text=claim["text"],
                    rating=review.get("textualRating") or "N/D",
                    publisher=review.get("publisher", {}).get("name") or "Desconhecido",
                    url=review.get("url"),
                    review_date=review.get("reviewDate"), claim_date=claim.get("claimDate"),
                    publisher_site=review["publisher"].get("site"), retrieval_provider="google_fact_check",
                )
            )
    return FactCheckSearch(results[:30], status="success" if results else "no_results")
