from __future__ import annotations

import json
import re

from speechlens.llm import LLMClient

QUERY_BUILDER_SYSTEM = """You generate web search queries for historical speech annotation.

You are given:
- speech_title
- annotation_question (PRIMARY — base queries on this)
- evidence_span
- context_window

Return JSON: {"queries": ["...", ...]} with 3-5 queries.

Rules:
- NEVER query only the highlight word or a single common noun (human, front, rights, Islam alone).
- Every query must include at least two of: Malcolm X, speech title fragment, 1964, civil rights, Nation of Islam, specific event/name.
- Resolve names (Cassius → Cassius Clay / Muhammad Ali; Mr. Muhammad → Elijah Muhammad).
- annotation_question drives what you search for, not the shortest substring.
"""

_SINGLE_WORD_BAD = re.compile(r"^(human|rights|front|islam|negro)$", re.I)


def build_queries_from_question(
    annotation_question: str,
    evidence_span: str,
    speech_title: str,
    context_window: str,
) -> list[str]:
    """Heuristic fallback — always speech-aware, never single-word."""
    title_bit = speech_title[:50] if speech_title else "Malcolm X speech"
    year = "1964" if "1964" in context_window or "1964" in speech_title else "1960s"
    q_lower = annotation_question.lower()
    ev_lower = evidence_span.lower()

    if "human rights" in q_lower or "human rights" in ev_lower:
        return [
            f"Malcolm X human rights civil rights United Nations {year}",
            f"Malcolm X civil rights versus human rights {year}",
            f"Malcolm X Declaration of Independence human rights {year}",
        ]
    if "racial front" in q_lower or "racial front" in ev_lower:
        return [
            f"Malcolm X explosive year racial struggle {year}",
            f"Malcolm X civil rights violence {year} press conference",
            f"Malcolm X Declaration of Independence {year} context",
        ]
    if "cassius" in ev_lower or "liston" in ev_lower or "joe louis" in ev_lower:
        return [
            "Cassius Clay Sonny Liston February 1964 fight Malcolm X",
            "Malcolm X Cassius Clay Liston 1964",
            "Joe Louis aging heavyweight champion history",
        ]
    if "muhammad" in ev_lower:
        return [
            f"Elijah Muhammad Nation of Islam Malcolm X separation {year}",
            f"Malcolm X Mr Muhammad analysis solution {year}",
            "Nation of Islam complete separation African homeland",
        ]
    if "american negro" in ev_lower or "so-called negro" in ev_lower:
        return [
            f"Malcolm X American Negro terminology {year}",
            "historical term Negro mid 20th century civil rights",
            f"Malcolm X Black terminology {year} speech",
        ]

    return [
        f"Malcolm X {title_bit} {year} {evidence_span[:60]}",
        f"{annotation_question[:80]} Malcolm X {year}",
        f"Malcolm X {evidence_span[:40]} civil rights history",
    ][:5]


def build_search_queries(
    transcript_title: str,
    segment_speaker: str | None,
    expanded_question: str,
    evidence_span: str,
    context_text: str,
    existing_queries: list[str],
    llm: LLMClient | None = None,
) -> list[str]:
    if existing_queries and not _queries_too_naive(existing_queries):
        return existing_queries[:5]

    llm = llm or LLMClient()
    user = json.dumps(
        {
            "speech_title": transcript_title,
            "segment_speaker": segment_speaker,
            "annotation_question": expanded_question,
            "evidence_span": evidence_span,
            "context_window": context_text,
        },
        indent=2,
    )
    try:
        result = llm.complete_json(QUERY_BUILDER_SYSTEM, user)
        queries = [q.strip() for q in result.get("queries", []) if q.strip()]
        queries = [q for q in queries if not _SINGLE_WORD_BAD.match(q.strip())]
        if queries and not _queries_too_naive(queries):
            return queries[:5]
    except Exception:
        pass

    return build_queries_from_question(
        expanded_question, evidence_span, transcript_title, context_text
    )


def _queries_too_naive(queries: list[str]) -> bool:
    for q in queries:
        words = q.strip().split()
        if len(words) <= 2:
            return True
        if _SINGLE_WORD_BAD.match(q.strip()):
            return True
    return False
