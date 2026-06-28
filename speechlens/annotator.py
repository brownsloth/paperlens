from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from speechlens.agents.annotation_writer import AnnotationWriter
from speechlens.agents.evidence_agent import EvidenceAgent
from speechlens.agents.span_expander import SpanExpander
from speechlens.annotation.renderer import export_html, export_json, export_markdown
from speechlens.config import settings
from speechlens.ingestion.service import IngestionService
from speechlens.models import AnnotateResponse, Annotation, AnnotationDepth, Transcript
from speechlens.retrieval.retrieval_agent import RetrievalAgent
from speechlens.segmentation.span_detector import SpanDetector


class AnnotatedDocument:
    def __init__(self, transcript: Transcript, annotations: list[Annotation], mode: AnnotationDepth):
        self.transcript = transcript
        self.annotations = annotations
        self.mode = mode

    @property
    def response(self) -> AnnotateResponse:
        return AnnotateResponse(
            doc_id=self.transcript.doc_id,
            title=self.transcript.title,
            segments=self.transcript.segments,
            annotations=self.annotations,
            metadata={"mode": self.mode.value, "web_search": settings.enable_web_search},
        )

    def to_markdown(self, path: str | Path) -> None:
        export_markdown(path, self.transcript, self.annotations)

    def to_html(self, path: str | Path) -> None:
        export_html(path, self.transcript, self.annotations)

    def to_json(self, path: str | Path) -> None:
        export_json(path, self.response)


class SpeechAnnotator:
    def __init__(
        self,
        mode: AnnotationDepth | str = AnnotationDepth.MEDIUM,
        require_sources: bool = True,
        human_review_threshold: float | None = None,
        enable_web_search: bool | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        if isinstance(mode, str):
            mode = AnnotationDepth(mode)
        self.mode = mode
        self.require_sources = require_sources
        if human_review_threshold is not None:
            settings.human_review_threshold = human_review_threshold
        if enable_web_search is not None:
            settings.enable_web_search = enable_web_search

        llm_kwargs: dict[str, str] = {}
        if api_key:
            llm_kwargs["api_key"] = api_key
        if model:
            llm_kwargs["model"] = model

        from speechlens.llm import LLMClient

        llm = LLMClient(**llm_kwargs) if llm_kwargs else LLMClient()
        self.ingestion = IngestionService()
        self.span_detector = SpanDetector(llm=llm)
        self.span_expander = SpanExpander(llm=llm)
        self.retrieval_agent = RetrievalAgent(llm=llm)
        self.evidence_agent = EvidenceAgent(llm=llm)
        self.annotation_writer = AnnotationWriter(llm=llm)

    def from_text(self, text: str, *, title: str | None = None) -> Transcript:
        return self.ingestion.from_text(text, title=title)

    def from_file(self, path: str | Path, *, title: str | None = None) -> Transcript:
        return self.ingestion.from_file(path, title=title)

    def from_url(self, url: str) -> Transcript:
        return self.ingestion.from_url(url)

    def annotate(
        self,
        transcript: Transcript,
        *,
        on_progress: Callable[[str, int, int], None] | None = None,
        checkpoint_path: Path | None = None,
    ) -> AnnotatedDocument:
        annotations: list[Annotation] = []
        segments = transcript.segments
        total_segments = len(segments)

        for seg_idx, segment in enumerate(segments, start=1):
            if on_progress:
                on_progress(
                    f"segment {seg_idx}/{total_segments}: detecting spans",
                    seg_idx,
                    total_segments,
                )
            spans = self.span_detector.detect(segment, self.mode)
            expanded_spans = self.span_expander.expand(transcript, segment, spans)
            for span_idx, expanded in enumerate(expanded_spans, start=1):
                if on_progress:
                    on_progress(
                        f"segment {seg_idx}/{total_segments}, span {span_idx}/{len(expanded_spans)}: "
                        f"\"{expanded.highlight_span[:40]}\"",
                        seg_idx,
                        total_segments,
                    )
                evidence_bundle = None
                evidence_score = None
                if self.require_sources:
                    if expanded.needs_web and settings.enable_web_search:
                        evidence_bundle = self.retrieval_agent.retrieve(transcript, segment, expanded)
                        evidence_score = self.evidence_agent.score(segment, expanded, evidence_bundle)
                    elif not expanded.needs_web:
                        from speechlens.retrieval.retrieval_agent import EvidenceBundle
                        from speechlens.segmentation.context import format_context_for_search, get_context_window

                        before, current, after = get_context_window(transcript, segment.segment_id)
                        evidence_bundle = EvidenceBundle(
                            highlight_span=expanded.highlight_span,
                            evidence_span=expanded.evidence_span,
                            annotation_question=expanded.annotation_question,
                            queries=[],
                            hits=[],
                            chunks=[],
                            context_text=format_context_for_search(before, current, after),
                        )
                        evidence_score = self.evidence_agent.score(segment, expanded, evidence_bundle)

                annotation = self.annotation_writer.write(
                    segment,
                    expanded,
                    require_sources=self.require_sources,
                    evidence_bundle=evidence_bundle,
                    evidence_score=evidence_score,
                )
                annotations.append(annotation)

                if checkpoint_path:
                    partial = AnnotatedDocument(transcript, list(annotations), self.mode)
                    partial.to_json(checkpoint_path)

        return AnnotatedDocument(transcript, annotations, self.mode)
