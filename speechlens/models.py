from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AnnotationDepth(str, Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    DENSE = "dense"


class EvidenceStatus(str, Enum):
    SUPPORTED = "supported"
    SUPPORTED_GENERAL_CONTEXT = "supported_general_context"
    PARTIALLY_SUPPORTED = "partially_supported"
    DISPUTED = "disputed"
    CONTRADICTED = "contradicted"
    UNCLEAR = "unclear"
    NOT_ENOUGH_EVIDENCE = "not_enough_evidence"
    NEEDS_VERIFICATION = "needs_verification"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class AnnotationType(str, Enum):
    ENTITY = "entity"
    HISTORICAL_CONTEXT = "historical_context"
    QUOTE_VERIFICATION = "quote_verification"
    DOCTRINAL_CONTEXT = "doctrinal_context"
    AMBIGUOUS_PHRASE = "ambiguous_phrase"
    RHETORICAL = "rhetorical"
    CLAIM_VERIFICATION = "claim_verification"


class Source(BaseModel):
    title: str
    url: str | None = None
    source_type: str = "secondary"
    quote: str | None = None
    relevance: str = "general"


class Segment(BaseModel):
    segment_id: str
    speaker: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    text: str


class CandidateSpan(BaseModel):
    span_text: str
    reason: str
    annotation_type: AnnotationType
    priority: int = Field(ge=1, le=5, default=3)


class Annotation(BaseModel):
    annotation_id: str
    segment_id: str
    span_start: int
    span_end: int
    span_text: str
    annotation_type: AnnotationType
    annotation_text: str
    evidence_status: EvidenceStatus
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[Source] = Field(default_factory=list)
    needs_human_review: bool = False
    alternative_interpretations: list[str] = Field(default_factory=list)


class Transcript(BaseModel):
    doc_id: str
    title: str
    date: str | None = None
    source_url: str | None = None
    speakers: list[str] = Field(default_factory=list)
    segments: list[Segment] = Field(default_factory=list)


class AnnotateRequest(BaseModel):
    text: str
    mode: AnnotationDepth = AnnotationDepth.MEDIUM
    require_sources: bool = True
    title: str | None = None


class AnnotateUrlRequest(BaseModel):
    url: str
    mode: AnnotationDepth = AnnotationDepth.MEDIUM
    require_sources: bool = True


class AnnotateResponse(BaseModel):
    doc_id: str
    title: str
    segments: list[Segment]
    annotations: list[Annotation]
    metadata: dict[str, Any] = Field(default_factory=dict)
