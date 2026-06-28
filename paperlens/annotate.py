from __future__ import annotations

import json
import uuid
from pathlib import Path

from speechlens.llm import LLMClient

from paperlens.chunking.structure import PaperChunk, build_annotation_candidates
from paperlens.models import (
    AnnotationLens,
    AnnotationTarget,
    PaperAnnotation,
    PaperAnnotationType,
    PaperBlock,
    PaperDocument,
    PaperMeta,
)
from paperlens.parse.pdf_blocks import extract_blocks_from_pdf
from paperlens.parse.render import render_pdf_pages
from paperlens.paths import PAPER_ANNOTATED_DIR, PAPER_BLOCKS_DIR
from paperlens.resolve import attach_bbox_to_annotations
from paperlens.sections import (
    annotatable_blocks,
    body_page_count,
    detect_reference_start_page,
    filter_annotatable_annotations,
    is_annotatable,
)
from paperlens.vision import VisionClient

_ANNOTATION_TYPES = [t.value for t in PaperAnnotationType]
_LENSES = [lens.value for lens in AnnotationLens]


def parse_paper(
    pdf_path: Path,
    *,
    paper_id: str,
    title: str,
    authors: list[str] | None = None,
    year: int | None = None,
    arxiv_id: str | None = None,
    abstract: str | None = None,
    force: bool = False,
) -> PaperDocument:
    pdf_path = Path(pdf_path)
    blocks = extract_blocks_from_pdf(str(pdf_path), paper_id)
    pages = render_pdf_pages(str(pdf_path), paper_id, force=force)
    ref_start = detect_reference_start_page(blocks)

    paper = PaperMeta(
        paper_id=paper_id,
        title=title,
        authors=authors or [],
        year=year,
        arxiv_id=arxiv_id,
        abstract=abstract,
        pdf_path=str(pdf_path),
        pdf_status="available",
        page_count=len(pages),
        block_count=len(blocks),
    )
    doc = PaperDocument(
        paper=paper,
        blocks=blocks,
        pages=pages,
        metadata={
            "reference_start_page": ref_start,
            "body_page_count": body_page_count(blocks),
            "annotatable_block_count": len(annotatable_blocks(blocks)),
        },
    )
    _save_parsed(doc)
    return doc


def _save_parsed(doc: PaperDocument) -> None:
    out = PAPER_BLOCKS_DIR / f"{doc.paper.paper_id}.json"
    out.write_text(doc.model_dump_json(indent=2), encoding="utf-8")


def load_parsed(paper_id: str) -> PaperDocument | None:
    path = PAPER_BLOCKS_DIR / f"{paper_id}.json"
    if not path.exists():
        return None
    return PaperDocument.model_validate_json(path.read_text(encoding="utf-8"))


def load_annotated(paper_id: str) -> PaperDocument | None:
    path = PAPER_ANNOTATED_DIR / f"{paper_id}.json"
    if not path.exists():
        return None
    return PaperDocument.model_validate_json(path.read_text(encoding="utf-8"))


class PaperAnnotator:
    def __init__(
        self,
        *,
        lens: AnnotationLens = AnnotationLens.BEGINNER,
        max_candidates: int = 12,
        llm: LLMClient | None = None,
        use_vision: bool = True,
    ):
        self.lens = lens
        self.max_candidates = max_candidates
        self.llm = llm or LLMClient()
        self.use_vision = use_vision
        self._vision: VisionClient | None = None

    def _vision_client(self) -> VisionClient | None:
        if not self.use_vision:
            return None
        if self._vision is None:
            try:
                self._vision = VisionClient()
            except ValueError:
                return None
        return self._vision

    def annotate(self, doc: PaperDocument) -> PaperDocument:
        candidates = build_annotation_candidates(doc.blocks, max_candidates=self.max_candidates)
        candidates = self._apply_vision(candidates, doc.blocks)
        if not candidates:
            return doc

        raw = self.llm.complete_json(
            system=_system_prompt(),
            user=_user_prompt(doc.paper.title, candidates, self.lens.value),
        )
        annotations = _parse_llm_annotations(raw, doc.paper.paper_id, doc.blocks, self.lens)
        annotated = doc.model_copy(
            update={
                "annotations": annotations,
                "metadata": {
                    **doc.metadata,
                    "lens": self.lens.value,
                    "candidate_count": len(candidates),
                },
            }
        )
        annotated.paper.has_annotations = True
        annotated.annotations = filter_annotatable_annotations(doc.blocks, annotations)
        out = PAPER_ANNOTATED_DIR / f"{doc.paper.paper_id}.json"
        out.write_text(annotated.model_dump_json(indent=2), encoding="utf-8")
        return annotated

    def _apply_vision(self, candidates: list[PaperChunk], blocks: list[PaperBlock]) -> list[PaperChunk]:
        vision = self._vision_client()
        if not vision:
            return candidates
        block_map = {b.block_id: b for b in blocks}
        enriched: list[PaperChunk] = []
        for chunk in candidates:
            if not chunk.image_crop_path:
                enriched.append(chunk)
                continue
            neighbor = _neighbor_context(chunk, block_map)
            try:
                description = vision.describe_crop(
                    chunk.image_crop_path,
                    prompt=chunk.annotation_question,
                    context=neighbor,
                )
            except Exception:
                enriched.append(chunk)
                continue
            text = description or chunk.text
            enriched.append(
                PaperChunk(
                    chunk_id=chunk.chunk_id,
                    paper_id=chunk.paper_id,
                    block_ids=chunk.block_ids,
                    block_type=chunk.block_type,
                    text=text[:2500],
                    section=chunk.section,
                    page=chunk.page,
                    annotation_question=chunk.annotation_question,
                    image_crop_path=chunk.image_crop_path,
                )
            )
        return enriched


def _system_prompt() -> str:
    return f"""You annotate research papers for readers. Return JSON:
{{
  "annotations": [
    {{
      "block_id": "p03_b012",
      "quote": "short exact phrase from the block (optional)",
      "annotation_type": one of {_ANNOTATION_TYPES},
      "annotation_text": "2-4 sentence explanation",
      "confidence": 0.0-1.0
    }}
  ]
}}

Rules:
- Reference block_id from the candidate list only. Never invent coordinates.
- quote must be an exact substring when provided.
- Match the requested reading lens.
- NEVER annotate references, bibliography, acknowledgments, or citation lists.
- Prefer equations, figures, key claims, and method paragraphs from the paper body only.
"""


def _user_prompt(title: str, candidates: list[PaperChunk], lens: str) -> str:
    lines = [f'Paper: "{title}"', f"Lens: {lens}", "", "Candidates:"]
    for idx, chunk in enumerate(candidates, start=1):
        primary_block = chunk.block_ids[0]
        preview = chunk.text[:600].replace("\n", " ")
        lines.append(
            f"{idx}. block_id={primary_block} type={chunk.block_type} section={chunk.section}\n"
            f"   question: {chunk.annotation_question}\n"
            f"   text: {preview}"
        )
    return "\n".join(lines)


def _parse_llm_annotations(
    raw: dict,
    paper_id: str,
    blocks: list[PaperBlock],
    lens: AnnotationLens,
) -> list[PaperAnnotation]:
    block_map = {b.block_id: b for b in blocks}
    annotations: list[PaperAnnotation] = []

    for item in raw.get("annotations") or []:
        block_id = item.get("block_id")
        block = block_map.get(block_id or "")
        if not block or not is_annotatable(block):
            continue
        ann_type = item.get("annotation_type", "concept_explanation")
        if ann_type not in _ANNOTATION_TYPES:
            ann_type = "concept_explanation"
        quote = item.get("quote")
        target = AnnotationTarget(block_id=block_id, quote=quote)
        annotations.append(
            PaperAnnotation(
                annotation_id=f"ann_{uuid.uuid4().hex[:10]}",
                paper_id=paper_id,
                target=target,
                annotation_type=PaperAnnotationType(ann_type),
                annotation_text=str(item.get("annotation_text", "")).strip(),
                confidence=float(item.get("confidence", 0.7)),
                lens=lens,
            )
        )

    return attach_bbox_to_annotations(blocks, annotations)


def _neighbor_context(chunk: PaperChunk, block_map: dict[str, PaperBlock]) -> str:
    texts: list[str] = []
    for block_id in chunk.block_ids:
        block = block_map.get(block_id)
        if block and block.text:
            texts.append(block.text)
    return "\n".join(texts)
