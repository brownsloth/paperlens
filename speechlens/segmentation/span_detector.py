from __future__ import annotations

import json

from speechlens.config import settings
from speechlens.llm import LLMClient
from speechlens.models import AnnotationDepth, AnnotationType, CandidateSpan, Segment

SPAN_DETECTOR_SYSTEM = """You are identifying parts of a historical speech that need annotation.

Return only spans that a modern reader may not understand without context.
Do not explain yet.

Return JSON with a "spans" array. Each span must have:
- span_text: exact substring from the segment (must appear verbatim)
- reason: short reason this needs annotation
- annotation_type: one of entity, historical_context, quote_verification, doctrinal_context, ambiguous_phrase
- priority: integer 1-5 (5 = most important)

Rules:
- Return at most {max_spans} spans per segment.
- Prefer high-value references over obvious words.
- Do not annotate common English words unless historically loaded.
- span_text must be copied exactly from the segment text.
"""

DEPTH_GUIDANCE = {
    AnnotationDepth.LIGHT: "Only annotate references a general reader likely needs (names, places, movements).",
    AnnotationDepth.MEDIUM: "Annotate historical, ideological, and doctrinal references plus ambiguous phrases.",
    AnnotationDepth.DENSE: "Annotate nearly every meaningful claim, reference, and rhetorical move.",
}


class SpanDetector:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def detect(self, segment: Segment, mode: AnnotationDepth) -> list[CandidateSpan]:
        system = SPAN_DETECTOR_SYSTEM.format(max_spans=settings.max_spans_per_segment)
        user = json.dumps(
            {
                "segment_id": segment.segment_id,
                "speaker": segment.speaker,
                "text": segment.text,
                "depth_guidance": DEPTH_GUIDANCE[mode],
            },
            indent=2,
        )
        result = self.llm.complete_json(system, user)
        spans: list[CandidateSpan] = []
        for item in result.get("spans", []):
            span_text = item.get("span_text", "").strip()
            if not span_text or span_text not in segment.text:
                continue
            try:
                annotation_type = AnnotationType(item.get("annotation_type", "ambiguous_phrase"))
            except ValueError:
                annotation_type = AnnotationType.AMBIGUOUS_PHRASE
            spans.append(
                CandidateSpan(
                    span_text=span_text,
                    reason=item.get("reason", ""),
                    annotation_type=annotation_type,
                    priority=int(item.get("priority", 3)),
                )
            )
        spans.sort(key=lambda s: s.priority, reverse=True)
        return spans[: settings.max_spans_per_segment]
