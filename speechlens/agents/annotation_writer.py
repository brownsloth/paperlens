from __future__ import annotations

import json
import uuid

from speechlens.config import settings
from speechlens.llm import LLMClient
from speechlens.models import (
    Annotation,
    AnnotationType,
    CandidateSpan,
    EvidenceStatus,
    Segment,
    Source,
)

ANNOTATION_WRITER_SYSTEM = """Write a concise annotation for a reader of a historical speech.

Rules:
- preserve uncertainty; never invent attribution or fake quotes
- do not moralize or rewrite the speaker's intent
- separate fact from interpretation
- mention when evidence is weak
- write annotation_text in 2-4 sentences
- cite plausible source categories (books, archives, speeches) even if you lack exact URLs
- for quote_verification spans, say needs_verification unless you are highly confident

Return JSON with:
- annotation_text: string
- evidence_status: one of supported, supported_general_context, partially_supported, disputed, contradicted, unclear, not_enough_evidence, needs_verification
- confidence: float 0-1
- sources: array of {title, url (optional), source_type, quote (optional), relevance}
- alternative_interpretations: array of strings (empty if none)
- needs_human_review: boolean
"""


class AnnotationWriter:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def write(
        self,
        segment: Segment,
        span: CandidateSpan,
        *,
        require_sources: bool = True,
    ) -> Annotation:
        span_start = segment.text.index(span.span_text)
        span_end = span_start + len(span.span_text)

        user = json.dumps(
            {
                "segment": {
                    "segment_id": segment.segment_id,
                    "speaker": segment.speaker,
                    "text": segment.text,
                },
                "span": span.model_dump(),
                "require_sources": require_sources,
            },
            indent=2,
        )
        result = self.llm.complete_json(ANNOTATION_WRITER_SYSTEM, user)

        evidence_status = _parse_evidence_status(result.get("evidence_status", "unclear"))
        confidence = float(result.get("confidence", 0.5))
        needs_review = bool(result.get("needs_human_review", False))
        if confidence < settings.human_review_threshold:
            needs_review = True
        if evidence_status in {
            EvidenceStatus.NEEDS_VERIFICATION,
            EvidenceStatus.NOT_ENOUGH_EVIDENCE,
            EvidenceStatus.UNCLEAR,
        }:
            needs_review = True

        sources = [
            Source(
                title=s.get("title", "Unknown source"),
                url=s.get("url"),
                source_type=s.get("source_type", "secondary"),
                quote=s.get("quote"),
                relevance=s.get("relevance", "general"),
            )
            for s in result.get("sources", [])
        ]

        return Annotation(
            annotation_id=f"ann_{uuid.uuid4().hex[:10]}",
            segment_id=segment.segment_id,
            span_start=span_start,
            span_end=span_end,
            span_text=span.span_text,
            annotation_type=span.annotation_type,
            annotation_text=result.get("annotation_text", "").strip(),
            evidence_status=evidence_status,
            confidence=confidence,
            sources=sources,
            needs_human_review=needs_review,
            alternative_interpretations=result.get("alternative_interpretations", []),
        )


def _parse_evidence_status(value: str) -> EvidenceStatus:
    try:
        return EvidenceStatus(value)
    except ValueError:
        return EvidenceStatus.UNCLEAR
