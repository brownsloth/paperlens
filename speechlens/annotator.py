from __future__ import annotations

from pathlib import Path

from speechlens.agents.annotation_writer import AnnotationWriter
from speechlens.annotation.renderer import export_html, export_json, export_markdown
from speechlens.ingestion.service import IngestionService
from speechlens.models import AnnotateResponse, Annotation, AnnotationDepth, Transcript
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
            metadata={"mode": self.mode.value},
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
        api_key: str | None = None,
        model: str | None = None,
    ):
        if isinstance(mode, str):
            mode = AnnotationDepth(mode)
        self.mode = mode
        self.require_sources = require_sources
        if human_review_threshold is not None:
            from speechlens.config import settings

            settings.human_review_threshold = human_review_threshold

        llm_kwargs: dict[str, str] = {}
        if api_key:
            llm_kwargs["api_key"] = api_key
        if model:
            llm_kwargs["model"] = model

        from speechlens.llm import LLMClient

        llm = LLMClient(**llm_kwargs) if llm_kwargs else LLMClient()
        self.ingestion = IngestionService()
        self.span_detector = SpanDetector(llm=llm)
        self.annotation_writer = AnnotationWriter(llm=llm)

    def from_text(self, text: str, *, title: str | None = None) -> Transcript:
        return self.ingestion.from_text(text, title=title)

    def from_file(self, path: str | Path, *, title: str | None = None) -> Transcript:
        return self.ingestion.from_file(path, title=title)

    def from_url(self, url: str) -> Transcript:
        return self.ingestion.from_url(url)

    def annotate(self, transcript: Transcript) -> AnnotatedDocument:
        annotations: list[Annotation] = []
        for segment in transcript.segments:
            spans = self.span_detector.detect(segment, self.mode)
            for span in spans:
                annotation = self.annotation_writer.write(
                    segment,
                    span,
                    require_sources=self.require_sources,
                )
                annotations.append(annotation)
        return AnnotatedDocument(transcript, annotations, self.mode)
