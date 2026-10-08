from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

MAX_ANALYSIS_URL_LENGTH = 512


class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)


class UrlRequest(BaseModel):
    # Match the existing PostgreSQL source_url column until a versioned schema
    # migration can safely widen it. Normalized and redirected URLs are checked
    # again by the route; no part of an address may be silently discarded.
    url: str = Field(..., min_length=5, max_length=MAX_ANALYSIS_URL_LENGTH,
                     description="URL de até 512 caracteres, incluindo http:// ou https://; redirecionamentos têm o mesmo limite.")

    @field_validator("url", mode="before")
    @classmethod
    def trim_url(cls, value):
        return value.strip() if isinstance(value, str) else value


class FactCheckResult(BaseModel):
    claim_text: str
    rating:     str
    publisher:  str
    url:        Optional[str] = None
    review_date: Optional[str] = None
    claim_date: Optional[str] = None
    publisher_site: Optional[str] = None
    retrieval_provider: Optional[str] = None


class AnalysisResponse(BaseModel):
    score:               int
    semantic_score:      int
    domain_score:        int
    sensationalism:      int
    verdict:             str
    summary:             str
    red_flags:           List[str]
    positive_signals:    List[str]
    logical_fallacies:   List[str]
    emotional_triggers:  bool
    fact_checks:         List[FactCheckResult]
    domain_note:         str
    source_url:          Optional[str] = None
    recommended_sources: List[str] = []
    hive_result:         Optional[dict] = None
