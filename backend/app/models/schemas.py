from pydantic import BaseModel, Field
from typing import List, Optional


class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)


class UrlRequest(BaseModel):
    url: str = Field(..., min_length=5)


class FactCheckResult(BaseModel):
    claim_text: str
    rating:     str
    publisher:  str
    url:        Optional[str] = None


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
