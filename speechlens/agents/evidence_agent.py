from __future__ import annotations

import json

from speechlens.llm import LLMClient
from speechlens.models import ExpandedSpan, EvidenceStatus, Segment
from speechlens.retrieval.retrieval_agent import EvidenceBundle

EVIDENCE_AGENT_SYSTEM = """You score whether retrieved sources support an annotation for a historical speech.

Do not use outside knowledge beyond provided evidence.

Given annotation_question, evidence_span, context_window, and retrieved sources, return JSON with:
- evidence_status: overall label for the annotation
- confidence: float 0-1 for overall
- explanation: short reason
- needs_human_review: boolean
- supporting_quotes: array of {url, quote} from evidence only
- source_assessment: one sentence on source quality
- factual_claims: array of {claim, evidence_status, confidence} for verifiable facts only
- interpretive_claims: array of {claim, evidence_status, confidence} for readings of the exchange

Rules:
- Split biographical facts (e.g. Joe Louis was champion) from interpretive readings (speaker uses Louis to illustrate aging).
- factual_claims use: supported, partially_supported, not_enough_evidence, needs_verification
- interpretive_claims use: interpretive_from_transcript, supported_general_context, unclear
- Do not mark a sourced biographical fact as not_enough_evidence because interpretation is uncertain.
"""


class EvidenceAgent:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def score(
        self,
        segment: Segment,
        expanded: ExpandedSpan,
        bundle: EvidenceBundle,
    ) -> dict:
        if not expanded.needs_web:
            return {
                "evidence_status": EvidenceStatus.SUPPORTED_GENERAL_CONTEXT.value,
                "confidence": 0.78,
                "explanation": "Explained from transcript context; web search skipped.",
                "needs_human_review": False,
                "supporting_quotes": [],
                "source_assessment": "No web retrieval required.",
                "factual_claims": [],
                "interpretive_claims": [
                    {
                        "claim": bundle.annotation_question,
                        "evidence_status": "interpretive_from_transcript",
                        "confidence": 0.78,
                    }
                ],
            }

        if not bundle.chunks:
            return {
                "evidence_status": EvidenceStatus.NOT_ENOUGH_EVIDENCE.value,
                "confidence": 0.35,
                "explanation": "No quality web sources retrieved for this question.",
                "needs_human_review": True,
                "supporting_quotes": [],
                "source_assessment": "No usable sources after filtering.",
                "factual_claims": [],
                "interpretive_claims": [],
            }

        evidence = [
            {
                "title": c.title,
                "url": c.url,
                "source_type": c.source_type,
                "excerpt": c.excerpt[:1200],
            }
            for c in bundle.chunks
        ]
        user = json.dumps(
            {
                "segment": {"speaker": segment.speaker, "text": segment.text},
                "highlight_span": expanded.highlight_span,
                "evidence_span": expanded.evidence_span,
                "annotation_question": bundle.annotation_question,
                "annotation_type": expanded.annotation_type.value,
                "context_window": bundle.context_text,
                "queries_used": bundle.queries,
                "evidence": evidence,
            },
            indent=2,
        )
        return self.llm.complete_json(EVIDENCE_AGENT_SYSTEM, user)
