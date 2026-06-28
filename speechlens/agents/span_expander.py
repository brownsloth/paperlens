from __future__ import annotations

import json
import re

from speechlens.llm import LLMClient
from speechlens.models import AnnotationType, CandidateSpan, ExpandedSpan, Segment, Transcript
from speechlens.retrieval.query_builder import build_queries_from_question
from speechlens.segmentation.context import format_context_for_search, get_context_window

SPAN_EXPANDER_SYSTEM = """You prepare speech annotations for source-backed web research.

For each candidate highlight span, produce:
- highlight_span: short UI highlight (usually the original span)
- evidence_span: smallest complete phrase/sentence/passage needed to understand the claim
- annotation_type: choose the BEST type:
  entity, historical_context, quote_verification, doctrinal_context, political_framing,
  historical_term, period_language, rhetorical_phrase, common_metaphor, boxing_context,
  claim_verification, ambiguous_phrase
- annotation_question: the specific question the annotation must answer (not generic)
- needs_web: false for common metaphors (Father Time), obvious rhetoric, dictionary phrases
- search_queries: 3-5 queries derived FROM annotation_question + evidence_span + context
  NEVER use a single common word alone (bad: "human rights", "front", "human")
  ALWAYS include speaker name, speech title/date, and historical context in queries

Type rules:
- Father Time / aging metaphors in boxing talk → common_metaphor or rhetorical_phrase, needs_web false
- American Negro, so-called Negro → historical_term or period_language
- human rights in civil rights speech → political_framing (not doctrinal_context)
- racial front / explosive year → political_framing or historical_context
- Islam as identity line → doctrinal_context only if about beliefs; else entity
- Mr. Muhammad + analysis/solution → doctrinal_context with full claim clause as evidence_span
- Cassius/Liston/Joe Louis → boxing_context or entity with fight names and dates in queries

Return JSON: {"expanded": [ {...}, ... ]} one entry per input span, same order.
"""

COMMON_PHRASE_WEB_SKIP = re.compile(
    r"\b(father time|only time will tell|actions speak louder)\b",
    re.I,
)

PERIOD_TERMS = re.compile(r"\b(American Negro|so-called Negro|Negro)\b", re.I)


class SpanExpander:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def expand(
        self,
        transcript: Transcript,
        segment: Segment,
        spans: list[CandidateSpan],
    ) -> list[ExpandedSpan]:
        if not spans:
            return []

        before, current, after = get_context_window(transcript, segment.segment_id)
        context_text = format_context_for_search(before, current, after)
        context_ids = [s.segment_id for s in before + [current] + after]

        user = json.dumps(
            {
                "speech_title": transcript.title,
                "segment_id": segment.segment_id,
                "context_segment_ids": context_ids,
                "context_text": context_text,
                "spans": [s.model_dump() for s in spans],
            },
            indent=2,
        )

        try:
            result = self.llm.complete_json(SPAN_EXPANDER_SYSTEM, user)
            expanded_items = result.get("expanded", [])
            out: list[ExpandedSpan] = []
            for span, item in zip(spans, expanded_items, strict=False):
                out.append(
                    _to_expanded(span, item, context_ids, segment.text, transcript.title, context_text)
                )
            if len(out) == len(spans):
                return out
        except Exception:
            pass

        return [
            _heuristic_expand(span, segment, before, after, context_ids, transcript.title, context_text)
            for span in spans
        ]


def _parse_annotation_type(value: str, fallback: AnnotationType) -> AnnotationType:
    try:
        return AnnotationType(value)
    except ValueError:
        return fallback


def _to_expanded(
    span: CandidateSpan,
    item: dict,
    context_ids: list[str],
    segment_text: str,
    speech_title: str,
    context_text: str,
) -> ExpandedSpan:
    highlight = item.get("highlight_span") or span.span_text
    evidence = item.get("evidence_span") or span.span_text
    if evidence not in segment_text and span.span_text in segment_text:
        evidence = _expand_to_sentence(segment_text, span.span_text)

    ann_type = _parse_annotation_type(item.get("annotation_type", ""), span.annotation_type)
    question = item.get("annotation_question", "").strip()
    if not question:
        question = _derive_question(highlight, evidence, ann_type, context_text)

    needs_web = bool(item.get("needs_web", True))
    needs_web = _apply_needs_web_rules(highlight, evidence, ann_type, context_text, needs_web)

    queries = [q.strip() for q in item.get("search_queries", []) if q.strip()]
    if needs_web and (not queries or _queries_too_naive(queries, highlight)):
        queries = build_queries_from_question(question, evidence, speech_title, context_text)

    return ExpandedSpan(
        highlight_span=highlight if highlight in segment_text else span.span_text,
        evidence_span=evidence,
        reason=span.reason,
        annotation_type=ann_type,
        priority=span.priority,
        annotation_question=question,
        needs_web=needs_web,
        search_queries=queries[:5],
        context_segment_ids=item.get("context_segment_ids") or context_ids,
    )


def _heuristic_expand(
    span: CandidateSpan,
    segment: Segment,
    before: list[Segment],
    after: list[Segment],
    context_ids: list[str],
    speech_title: str,
    context_text: str,
) -> ExpandedSpan:
    evidence = _expand_to_sentence(segment.text, span.span_text)
    if len(span.span_text.split()) <= 2 and span.annotation_type == AnnotationType.ENTITY:
        evidence = segment.text.strip()

    ann_type = _reclassify_type(span, evidence, context_text)
    question = _derive_question(span.span_text, evidence, ann_type, context_text)
    needs_web = _apply_needs_web_rules(span.span_text, evidence, ann_type, context_text, True)
    queries = (
        build_queries_from_question(question, evidence, speech_title, context_text) if needs_web else []
    )

    return ExpandedSpan(
        highlight_span=span.span_text,
        evidence_span=evidence,
        reason=span.reason,
        annotation_type=ann_type,
        priority=span.priority,
        annotation_question=question,
        needs_web=needs_web,
        search_queries=queries,
        context_segment_ids=context_ids,
    )


def _reclassify_type(span: CandidateSpan, evidence: str, context: str) -> AnnotationType:
    hl = span.span_text.lower()
    ctx = (evidence + " " + context).lower()
    if COMMON_PHRASE_WEB_SKIP.search(hl):
        return AnnotationType.COMMON_METAPHOR
    if PERIOD_TERMS.search(hl):
        return AnnotationType.HISTORICAL_TERM
    if "human rights" in hl or "human rights" in evidence.lower():
        return AnnotationType.POLITICAL_FRAMING
    if "racial front" in hl or "racial front" in evidence.lower():
        return AnnotationType.POLITICAL_FRAMING
    if any(k in ctx for k in ("liston", "cassius", "joe louis", "heavyweight", "fight")):
        if hl in {"cassius", "liston"} or "joe louis" in hl:
            return AnnotationType.BOXING_CONTEXT
    if "muhammad" in hl and ("analysis" in evidence.lower() or "solution" in evidence.lower()):
        return AnnotationType.DOCTRINAL_CONTEXT
    if hl == "islam" and len(evidence.split()) < 8:
        return AnnotationType.DOCTRINAL_CONTEXT
    return span.annotation_type


def _derive_question(highlight: str, evidence: str, ann_type: AnnotationType, context: str) -> str:
    if ann_type == AnnotationType.BOXING_CONTEXT:
        return f"Who or what does '{highlight}' refer to in this boxing exchange, and what fight or date is relevant?"
    if ann_type == AnnotationType.POLITICAL_FRAMING:
        return f"Why does the speaker use '{highlight}' here, and what political framing does it carry in 1960s civil rights context?"
    if ann_type == AnnotationType.HISTORICAL_TERM:
        return f"What did the term '{highlight}' mean in this historical period, and why might it matter to readers today?"
    if ann_type == AnnotationType.DOCTRINAL_CONTEXT:
        return f"What doctrine or political position is expressed in: \"{evidence[:120]}\"?"
    if ann_type in {AnnotationType.COMMON_METAPHOR, AnnotationType.RHETORICAL_PHRASE}:
        return f"What does the speaker mean by '{highlight}' in this specific exchange?"
    if ann_type == AnnotationType.ENTITY:
        return f"Who or what is '{highlight}' in this context?"
    return f"What should a modern reader understand about '{highlight}' given: \"{evidence[:100]}\"?"


def _apply_needs_web_rules(
    highlight: str,
    evidence: str,
    ann_type: AnnotationType,
    context: str,
    default: bool,
) -> bool:
    if ann_type in {AnnotationType.COMMON_METAPHOR, AnnotationType.RHETORICAL_PHRASE}:
        return False
    if COMMON_PHRASE_WEB_SKIP.search(highlight):
        return False
    if ann_type in {
        AnnotationType.POLITICAL_FRAMING,
        AnnotationType.HISTORICAL_CONTEXT,
        AnnotationType.QUOTE_VERIFICATION,
        AnnotationType.CLAIM_VERIFICATION,
        AnnotationType.BOXING_CONTEXT,
        AnnotationType.DOCTRINAL_CONTEXT,
        AnnotationType.ENTITY,
        AnnotationType.HISTORICAL_TERM,
    }:
        return True
    return default


def _queries_too_naive(queries: list[str], highlight: str) -> bool:
    hl_words = highlight.lower().split()
    for q in queries:
        q_lower = q.lower().strip()
        if q_lower in {highlight.lower(), hl_words[0] if hl_words else ""}:
            return True
        if len(q_lower.split()) <= 2 and not any(
            k in q_lower for k in ("malcolm", "1964", "civil rights", "clay", "liston")
        ):
            return True
    return False


def _expand_to_sentence(text: str, anchor: str) -> str:
    if anchor not in text:
        return anchor
    idx = text.index(anchor)
    start = text.rfind(".", 0, idx)
    start = 0 if start == -1 else start + 1
    end = text.find(".", idx + len(anchor))
    end = len(text) if end == -1 else end + 1
    chunk = text[start:end].strip()
    return chunk if len(chunk) > len(anchor) else text[max(0, idx - 80) : idx + len(anchor) + 120].strip()
