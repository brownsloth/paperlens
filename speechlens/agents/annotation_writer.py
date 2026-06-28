from __future__ import annotations

import json
import uuid

from speechlens.config import settings
from speechlens.llm import LLMClient
from speechlens.models import (
    Annotation,
    ClaimComponent,
    EvidenceStatus,
    ExpandedSpan,
    Segment,
    Source,
)
from speechlens.retrieval.retrieval_agent import EvidenceBundle

ANNOTATION_WRITER_SYSTEM = """Write a concise annotation for a reader of a historical speech.

You must answer ONLY the annotation_question — do not summarize the whole speech or paragraph.

Given:
- highlight_span (what reader clicked)
- evidence_span (passage being explained — stay within this scope)
- annotation_question
- factual_claims and interpretive_claims from evidence scorer (if any)
- context_window and retrieved evidence (if any)

Rules:
- 2-4 sentences max; answer annotation_question directly
- If evidence_span is one sentence, do not discuss unrelated themes from the paragraph
- Separate sourced facts from interpretive reading in prose when both exist
- preserve uncertainty; never invent quotes or attribution
- cite filtered sources with URLs when used
- if no web sources, explain from transcript context only

Return JSON with:
- annotation_text: string
- evidence_status: use evidence_score overall unless strong reason
- confidence: float 0-1
- sources: array of {title, url, source_type, quote, relevance}
- alternative_interpretations: array of strings
- needs_human_review: boolean
"""


class AnnotationWriter:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def write(
        self,
        segment: Segment,
        expanded: ExpandedSpan,
        *,
        require_sources: bool = True,
        evidence_bundle: EvidenceBundle | None = None,
        evidence_score: dict | None = None,
    ) -> Annotation:
        highlight = expanded.highlight_span
        if highlight not in segment.text:
            highlight = expanded.evidence_span if expanded.evidence_span in segment.text else highlight
        span_start = segment.text.index(highlight) if highlight in segment.text else 0
        span_end = span_start + len(highlight)

        question = expanded.annotation_question or evidence_bundle.annotation_question if evidence_bundle else ""

        payload: dict = {
            "segment": {
                "segment_id": segment.segment_id,
                "speaker": segment.speaker,
                "text": segment.text,
            },
            "highlight_span": expanded.highlight_span,
            "evidence_span": expanded.evidence_span,
            "annotation_question": question,
            "annotation_type": expanded.annotation_type.value,
            "require_sources": require_sources,
            "needs_web": expanded.needs_web,
            "scope_rule": "Answer only annotation_question; do not exceed evidence_span scope.",
        }
        if evidence_bundle:
            payload["context_window"] = evidence_bundle.context_text
            if evidence_bundle.chunks:
                payload["retrieved_evidence"] = [
                    {
                        "title": c.title,
                        "url": c.url,
                        "source_type": c.source_type,
                        "excerpt": c.excerpt[:1500],
                    }
                    for c in evidence_bundle.chunks
                ]
                payload["search_queries"] = evidence_bundle.queries
        if evidence_score:
            payload["evidence_score"] = evidence_score
            payload["factual_claims"] = evidence_score.get("factual_claims", [])
            payload["interpretive_claims"] = evidence_score.get("interpretive_claims", [])

        result = self.llm.complete_json(ANNOTATION_WRITER_SYSTEM, json.dumps(payload, indent=2))

        evidence_status = _parse_evidence_status(
            result.get("evidence_status")
            or (evidence_score or {}).get("evidence_status", "unclear")
        )
        confidence = float(
            result.get("confidence") or (evidence_score or {}).get("confidence", 0.5)
        )
        needs_review = bool(
            result.get("needs_human_review")
            or (evidence_score or {}).get("needs_human_review", False)
        )
        if confidence < settings.human_review_threshold:
            needs_review = True
        if evidence_status in {
            EvidenceStatus.NEEDS_VERIFICATION,
            EvidenceStatus.NOT_ENOUGH_EVIDENCE,
            EvidenceStatus.UNCLEAR,
        }:
            needs_review = True

        sources = _merge_sources(result, evidence_bundle, evidence_score)
        factual = _parse_claims((evidence_score or {}).get("factual_claims", []))
        interpretive = _parse_claims((evidence_score or {}).get("interpretive_claims", []))

        return Annotation(
            annotation_id=f"ann_{uuid.uuid4().hex[:10]}",
            segment_id=segment.segment_id,
            span_start=span_start,
            span_end=span_end,
            span_text=highlight,
            annotation_type=expanded.annotation_type,
            annotation_text=result.get("annotation_text", "").strip(),
            evidence_status=evidence_status,
            confidence=confidence,
            sources=sources,
            needs_human_review=needs_review,
            alternative_interpretations=result.get("alternative_interpretations", []),
            evidence_span=expanded.evidence_span,
            annotation_question=question or None,
            factual_claims=factual,
            interpretive_claims=interpretive,
        )


def _parse_claims(items: list) -> list[ClaimComponent]:
    out: list[ClaimComponent] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("claim"):
            continue
        out.append(
            ClaimComponent(
                claim=item["claim"],
                evidence_status=item.get("evidence_status", "unclear"),
                confidence=float(item.get("confidence", 0.5)),
            )
        )
    return out


def _merge_sources(
    result: dict,
    evidence_bundle: EvidenceBundle | None,
    evidence_score: dict | None,
) -> list[Source]:
    sources: list[Source] = []
    seen: set[str] = set()

    for s in result.get("sources", []):
        url = s.get("url") or ""
        key = url or s.get("title", "")
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            Source(
                title=s.get("title", "Unknown source"),
                url=s.get("url"),
                source_type=s.get("source_type", "secondary"),
                quote=s.get("quote"),
                relevance=s.get("relevance", "general"),
            )
        )

    if evidence_bundle:
        for chunk in evidence_bundle.chunks:
            if chunk.url in seen:
                continue
            seen.add(chunk.url)
            sources.append(
                Source(
                    title=chunk.title,
                    url=chunk.url,
                    source_type=chunk.source_type,
                    relevance="retrieved",
                )
            )

    for sq in (evidence_score or {}).get("supporting_quotes", []):
        url = sq.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        sources.append(
            Source(
                title=url,
                url=url,
                source_type="web",
                quote=sq.get("quote"),
                relevance="direct",
            )
        )

    return sources


def _parse_evidence_status(value: str) -> EvidenceStatus:
    try:
        return EvidenceStatus(value)
    except ValueError:
        return EvidenceStatus.UNCLEAR
