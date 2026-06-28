from __future__ import annotations

import time
import uuid

from speechlens.llm import LLMClient

from paperlens.annotate import load_annotated, load_parsed
from paperlens.models import (
    AnnotationLens,
    AnnotationTarget,
    BBox,
    PaperAnnotation,
    PaperAnnotationType,
    PaperChatMessage,
    PaperDocument,
)
from paperlens.parse.crop import crop_page_region
from paperlens.paths import PAPER_ANNOTATED_DIR
from paperlens.resolve import attach_bbox_to_annotations, resolve_annotation_bbox, resolve_quote_span
from paperlens.sections import block_zone
from paperlens.vision import VisionClient


def require_parsed(paper_id: str) -> PaperDocument:
    doc = load_annotated(paper_id) or load_parsed(paper_id)
    if not doc:
        raise FileNotFoundError(f"Paper not parsed: {paper_id}")
    return doc


def save_document(doc: PaperDocument) -> PaperDocument:
    if doc.annotations:
        doc.paper.has_annotations = True
    out = PAPER_ANNOTATED_DIR / f"{doc.paper.paper_id}.json"
    PAPER_ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    return doc


def _user_annotatable(block) -> bool:
    return block_zone(block) not in ("acknowledgments",)


DEFAULT_HIGHLIGHT_COLOR = "#FDE047"
DEFAULT_NOTE_COLOR = "#93C5FD"


def create_annotation(
    paper_id: str,
    *,
    block_id: str,
    annotation_text: str,
    annotation_type: str = "concept_explanation",
    quote: str | None = None,
    lens: AnnotationLens = AnnotationLens.BEGINNER,
    color: str | None = None,
) -> PaperDocument:
    doc = require_parsed(paper_id)
    block = next((b for b in doc.blocks if b.block_id == block_id), None)
    if not block or not _user_annotatable(block):
        raise ValueError(f"Block {block_id} is not annotatable")

    ann_type = annotation_type
    if ann_type not in {t.value for t in PaperAnnotationType}:
        ann_type = PaperAnnotationType.CONCEPT_EXPLANATION.value

    annotation = PaperAnnotation(
        annotation_id=f"ann_{uuid.uuid4().hex[:10]}",
        paper_id=paper_id,
        target=AnnotationTarget(block_id=block_id, quote=quote),
        annotation_type=PaperAnnotationType(ann_type),
        annotation_text=annotation_text.strip(),
        lens=lens,
        evidence_status="user_authored",
        color=color or DEFAULT_NOTE_COLOR,
    )
    doc.annotations.append(annotation)
    doc.annotations = attach_bbox_to_annotations(doc.blocks, doc.annotations)
    return save_document(doc)


def update_annotation(
    paper_id: str,
    annotation_id: str,
    *,
    annotation_text: str | None = None,
    annotation_type: str | None = None,
    color: str | None = None,
) -> PaperDocument:
    doc = require_parsed(paper_id)
    idx = next((i for i, a in enumerate(doc.annotations) if a.annotation_id == annotation_id), None)
    if idx is None:
        raise FileNotFoundError(f"Annotation not found: {annotation_id}")

    ann = doc.annotations[idx]
    updates: dict = {}
    if annotation_text is not None:
        updates["annotation_text"] = annotation_text.strip()
    if annotation_type is not None and annotation_type in {t.value for t in PaperAnnotationType}:
        updates["annotation_type"] = PaperAnnotationType(annotation_type)
    if color is not None:
        updates["color"] = color
    doc.annotations[idx] = ann.model_copy(update=updates)
    return save_document(doc)


def delete_annotation(paper_id: str, annotation_id: str) -> PaperDocument:
    doc = require_parsed(paper_id)
    before = len(doc.annotations)
    doc.annotations = [a for a in doc.annotations if a.annotation_id != annotation_id]
    if len(doc.annotations) == before:
        raise FileNotFoundError(f"Annotation not found: {annotation_id}")
    if not doc.annotations:
        doc.paper.has_annotations = False
    return save_document(doc)


def _page_info(doc: PaperDocument, page: int):
    return next((p for p in doc.pages if p.page == page), None)


def _find_block_for_quote(doc: PaperDocument, page: int, quote: str, block_id: str | None):
    if block_id:
        block = next((b for b in doc.blocks if b.block_id == block_id), None)
        if block and _user_annotatable(block):
            return block
    quote = quote.strip()
    candidates = [b for b in doc.blocks if b.page == page and _user_annotatable(b) and b.text]
    for block in candidates:
        if quote in block.text:
            return block
    quote_lower = quote.lower()
    for block in candidates:
        if quote_lower in block.text.lower():
            return block
    if candidates:
        return min(candidates, key=lambda b: abs(len(b.text) - len(quote)))
    return None


def _block_for_region(doc: PaperDocument, page: int, bbox: BBox):
    best = None
    best_area = 0.0
    for block in doc.blocks:
        if block.page != page or not _user_annotatable(block):
            continue
        overlap = _bbox_overlap_area(block.bbox, bbox)
        if overlap > best_area:
            best_area = overlap
            best = block
    return best


def _bbox_overlap_area(a: BBox, b: BBox) -> float:
    x0 = max(a.x0, b.x0)
    y0 = max(a.y0, b.y0)
    x1 = min(a.x1, b.x1)
    y1 = min(a.y1, b.y1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def create_highlight(
    paper_id: str,
    *,
    page: int,
    quote: str,
    block_id: str | None = None,
    bbox: BBox | None = None,
    color: str | None = None,
) -> PaperDocument:
    doc = require_parsed(paper_id)
    block = _find_block_for_quote(doc, page, quote, block_id)
    if not block or not _user_annotatable(block):
        raise ValueError("Could not anchor highlight to paper text")

    start, end = resolve_quote_span(block, quote.strip())
    target = AnnotationTarget(
        block_id=block.block_id,
        quote=quote.strip(),
        char_start=start,
        char_end=end,
    )
    resolved_bbox = bbox if bbox is not None else resolve_annotation_bbox(block, char_start=start, char_end=end)
    annotation = PaperAnnotation(
        annotation_id=f"ann_{uuid.uuid4().hex[:10]}",
        paper_id=paper_id,
        target=target,
        annotation_type=PaperAnnotationType.HIGHLIGHT,
        annotation_text=quote.strip(),
        lens=AnnotationLens.BEGINNER,
        evidence_status="highlight",
        page=page,
        bbox=resolved_bbox,
        color=color or DEFAULT_HIGHLIGHT_COLOR,
    )
    doc.annotations.append(annotation)
    return save_document(doc)


def annotate_text_selection(
    paper_id: str,
    *,
    page: int,
    quote: str,
    question: str,
    block_id: str | None = None,
    bbox: BBox | None = None,
    lens: AnnotationLens = AnnotationLens.BEGINNER,
    color: str | None = None,
    llm: LLMClient | None = None,
) -> PaperDocument:
    doc = require_parsed(paper_id)
    block = _find_block_for_quote(doc, page, quote, block_id)
    if not block or not _user_annotatable(block):
        raise ValueError("Could not anchor selection to paper text")

    client = llm or LLMClient()
    raw = client.complete_json(
        system=(
            'Return JSON: {"annotation_text": "2-4 sentence explanation", '
            '"annotation_type": "concept_explanation|equation_intuition|implementation_hint|figure_explanation", '
            '"confidence": 0.0-1.0}'
        ),
        user=(
            f'Paper: "{doc.paper.title}"\n'
            f"Reader question: {question.strip()}\n"
            f"Selected text:\n{quote.strip()}\n\n"
            f"Surrounding block:\n{block.text[:2000]}"
        ),
    )
    ann_type = str(raw.get("annotation_type", "concept_explanation"))
    if ann_type not in {t.value for t in PaperAnnotationType if t != PaperAnnotationType.HIGHLIGHT}:
        ann_type = PaperAnnotationType.CONCEPT_EXPLANATION.value

    target = AnnotationTarget(block_id=block.block_id, quote=quote.strip())
    resolved_bbox = bbox if bbox is not None else resolve_annotation_bbox(block)
    annotation = PaperAnnotation(
        annotation_id=f"ann_{uuid.uuid4().hex[:10]}",
        paper_id=paper_id,
        target=target,
        annotation_type=PaperAnnotationType(ann_type),
        annotation_text=str(raw.get("annotation_text", "")).strip(),
        confidence=float(raw.get("confidence", 0.75)),
        lens=lens,
        evidence_status="user_requested",
        page=page,
        bbox=resolved_bbox,
        color=color or DEFAULT_NOTE_COLOR,
    )
    doc.annotations.append(annotation)
    return save_document(doc)


def annotate_region_selection(
    paper_id: str,
    *,
    page: int,
    bbox: BBox,
    question: str,
    lens: AnnotationLens = AnnotationLens.BEGINNER,
    color: str | None = None,
) -> PaperDocument:
    doc = require_parsed(paper_id)
    page_info = _page_info(doc, page)
    if not page_info:
        raise ValueError(f"Page {page} not found")

    ref_start = doc.metadata.get("reference_start_page")
    # References pages are readable and annotatable by the user.

    crop_path = crop_page_region(paper_id, page, bbox, page_info)
    block = _block_for_region(doc, page, bbox)
    if not block or not _user_annotatable(block):
        raise ValueError("No annotatable block near this region")

    try:
        vision = VisionClient()
        explanation = vision.describe_crop(
            str(crop_path),
            prompt=question.strip() or "Explain what this region of the paper shows.",
            context=block.text[:800],
        )
    except ValueError as exc:
        raise ValueError("Vision API required for region annotation (set OPENAI_API_KEY)") from exc

    annotation = PaperAnnotation(
        annotation_id=f"ann_{uuid.uuid4().hex[:10]}",
        paper_id=paper_id,
        target=AnnotationTarget(block_id=block.block_id, quote=None),
        annotation_type=PaperAnnotationType.FIGURE_EXPLANATION,
        annotation_text=explanation or "Could not explain this region.",
        confidence=0.72,
        lens=lens,
        evidence_status="vision_crop",
        page=page,
        bbox=bbox,
        color=color or DEFAULT_NOTE_COLOR,
    )
    doc.annotations.append(annotation)
    return save_document(doc)


def chat_on_annotation(
    paper_id: str,
    annotation_id: str,
    *,
    message: str,
    llm: LLMClient | None = None,
) -> tuple[PaperDocument, PaperChatMessage]:
    doc = require_parsed(paper_id)
    idx = next((i for i, a in enumerate(doc.annotations) if a.annotation_id == annotation_id), None)
    if idx is None:
        raise FileNotFoundError(f"Annotation not found: {annotation_id}")

    ann = doc.annotations[idx]
    block = next((b for b in doc.blocks if b.block_id == ann.target.block_id), None)
    block_text = (block.text[:2000] if block else "") or ""

    user_msg = PaperChatMessage(
        role="user",
        content=message.strip(),
        created_at=_now_iso(),
    )
    thread = [*ann.thread, user_msg]

    client = llm or LLMClient()
    history_lines = []
    for msg in ann.thread[-6:]:
        history_lines.append(f"{msg.role.upper()}: {msg.content}")
    history = "\n".join(history_lines) if history_lines else "(no prior messages)"

    raw = client.complete_json(
        system=_chat_system_prompt(),
        user=_chat_user_prompt(
            paper_title=doc.paper.title,
            block_text=block_text,
            annotation_type=ann.annotation_type.value,
            annotation_text=ann.annotation_text,
            history=history,
            question=message.strip(),
        ),
    )
    reply_text = str(raw.get("reply", "")).strip() or "I could not generate a reply."
    assistant_msg = PaperChatMessage(
        role="assistant",
        content=reply_text,
        created_at=_now_iso(),
    )
    thread.append(assistant_msg)
    doc.annotations[idx] = ann.model_copy(update={"thread": thread})
    save_document(doc)
    return doc, assistant_msg


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _chat_system_prompt() -> str:
    return """You help readers understand research papers in a threaded conversation about one annotation.
Return JSON: {"reply": "your response in 2-5 sentences"}
Stay grounded in the cited block text and existing annotation. Be clear and direct."""


def _chat_user_prompt(
    *,
    paper_title: str,
    block_text: str,
    annotation_type: str,
    annotation_text: str,
    history: str,
    question: str,
) -> str:
    return f"""Paper: {paper_title}
Block text:
{block_text}

Annotation type: {annotation_type}
Annotation:
{annotation_text}

Prior thread:
{history}

Reader question:
{question}"""
