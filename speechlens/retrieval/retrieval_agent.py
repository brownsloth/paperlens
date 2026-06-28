from __future__ import annotations

from dataclasses import dataclass

from speechlens.config import settings
from speechlens.llm import LLMClient
from speechlens.models import ExpandedSpan, Segment, Transcript
from speechlens.retrieval.fetch import RetrievedChunk, fetch_page_excerpt
from speechlens.retrieval.query_builder import build_search_queries
from speechlens.retrieval.search import SearchHit, web_search
from speechlens.retrieval.source_filter import filter_retrieved_chunks, filter_search_hits
from speechlens.segmentation.context import format_context_for_search, get_context_window


@dataclass
class EvidenceBundle:
    highlight_span: str
    evidence_span: str
    annotation_question: str
    queries: list[str]
    hits: list[SearchHit]
    chunks: list[RetrievedChunk]
    context_text: str


class RetrievalAgent:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm

    def retrieve(
        self,
        transcript: Transcript,
        segment: Segment,
        expanded: ExpandedSpan,
        *,
        enabled: bool | None = None,
    ) -> EvidenceBundle:
        before, current, after = get_context_window(transcript, segment.segment_id)
        context_text = format_context_for_search(before, current, after)
        question = expanded.annotation_question or expanded.evidence_span

        if not expanded.needs_web:
            return EvidenceBundle(
                highlight_span=expanded.highlight_span,
                evidence_span=expanded.evidence_span,
                annotation_question=question,
                queries=[],
                hits=[],
                chunks=[],
                context_text=context_text,
            )

        enabled = settings.enable_web_search if enabled is None else enabled
        if not enabled:
            return EvidenceBundle(
                highlight_span=expanded.highlight_span,
                evidence_span=expanded.evidence_span,
                annotation_question=question,
                queries=[],
                hits=[],
                chunks=[],
                context_text=context_text,
            )

        queries = build_search_queries(
            transcript.title,
            segment.speaker,
            question,
            expanded.evidence_span,
            context_text,
            expanded.search_queries,
            llm=self.llm,
        )
        hits: list[SearchHit] = []
        seen_urls: set[str] = set()

        for query in queries:
            for hit in web_search(query, max_results=settings.max_search_results):
                if hit.url in seen_urls:
                    continue
                seen_urls.add(hit.url)
                hits.append(hit)
                if len(hits) >= settings.max_retrieved_pages * 2:
                    break

        hits = filter_search_hits(hits)[: settings.max_retrieved_pages]

        chunks: list[RetrievedChunk] = []
        for hit in hits:
            chunk = fetch_page_excerpt(hit.url)
            if chunk:
                chunks.append(chunk)
            elif hit.snippet:
                chunks.append(
                    RetrievedChunk(
                        title=hit.title,
                        url=hit.url,
                        excerpt=hit.snippet[: settings.max_source_excerpt_chars],
                        source_type=hit.source_type,
                    )
                )

        chunks = filter_retrieved_chunks(chunks)

        return EvidenceBundle(
            highlight_span=expanded.highlight_span,
            evidence_span=expanded.evidence_span,
            annotation_question=question,
            queries=queries,
            hits=hits,
            chunks=chunks,
            context_text=context_text,
        )
