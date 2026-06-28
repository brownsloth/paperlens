from __future__ import annotations

import re

from paperlens.models import BlockType, PaperAnnotation, PaperBlock

BACK_MATTER_HEADINGS = re.compile(
    r"^(references|bibliography|acknowledg(e)?ments|appendix(\s+[a-z0-9]+)?)\s*$",
    re.I,
)
REFERENCE_LINE = re.compile(r"^(\[\d+\]|\d+\.\s+[A-Z\"'])")
CITATION_HEAVY = re.compile(r"\(\d{4}[a-z]?\)")


def detect_reference_start_page(blocks: list[PaperBlock]) -> int | None:
    for block in blocks:
        if block.block_type != BlockType.HEADING:
            continue
        text = block.text.strip()
        if BACK_MATTER_HEADINGS.match(text):
            lowered = text.lower()
            if "reference" in lowered or "bibliograph" in lowered:
                return block.page
    tail = _detect_reference_tail(blocks)
    return tail


def assign_zones(blocks: list[PaperBlock]) -> list[PaperBlock]:
    zone = "body"
    ref_heading_seen = False
    updated: list[PaperBlock] = []

    for block in blocks:
        text = block.text.strip()
        if block.block_type == BlockType.HEADING and BACK_MATTER_HEADINGS.match(text):
            lowered = text.lower()
            if "reference" in lowered or "bibliograph" in lowered:
                zone = "references"
                ref_heading_seen = True
            elif "acknowledg" in lowered:
                zone = "acknowledgments"
            elif "appendix" in lowered:
                zone = "appendix"

        meta = {**(block.metadata or {}), "zone": zone}
        updated.append(block.model_copy(update={"metadata": meta}))

    if not ref_heading_seen:
        ref_start = _detect_reference_tail(blocks)
        if ref_start is not None:
            updated = []
            for block in blocks:
                zone = "references" if block.page >= ref_start else "body"
                if zone == "body" and _looks_like_reference_entry(block):
                    zone = "references"
                meta = {**(block.metadata or {}), "zone": zone}
                updated.append(block.model_copy(update={"metadata": meta}))

    return updated


def _detect_reference_tail(blocks: list[PaperBlock]) -> int | None:
    if not blocks:
        return None
    max_page = max(b.page for b in blocks)
    candidate_pages = [p for p in range(max(max_page - 55, 1), max_page + 1)]
    ref_pages: list[int] = []
    for page in candidate_pages:
        page_blocks = [b for b in blocks if b.page == page]
        if not page_blocks:
            continue
        ref_like = sum(1 for b in page_blocks if _looks_like_reference_entry(b))
        if ref_like / len(page_blocks) >= 0.55:
            ref_pages.append(page)
    return min(ref_pages) if ref_pages else None


def _looks_like_reference_entry(block: PaperBlock) -> bool:
    text = block.text.strip()
    if block.block_type == BlockType.LIST_ITEM:
        return True
    if len(text) > 520:
        return False
    if REFERENCE_LINE.match(text):
        return True
    if text.count("(") >= 2 and CITATION_HEAVY.search(text) and len(text) < 380:
        return True
    return False


def block_zone(block: PaperBlock) -> str:
    return str((block.metadata or {}).get("zone", "body"))


def is_annotatable(block: PaperBlock) -> bool:
    zone = block_zone(block)
    if zone in ("references", "acknowledgments"):
        return False
    if block.block_type == BlockType.LIST_ITEM:
        return False
    if _looks_like_reference_entry(block):
        return False
    section = (block.section or "").lower()
    if any(k in section for k in ("reference", "bibliograph", "acknowledg")):
        return False
    return True


def annotatable_blocks(blocks: list[PaperBlock]) -> list[PaperBlock]:
    return [b for b in blocks if is_annotatable(b)]


def body_page_count(blocks: list[PaperBlock]) -> int:
    pages = [b.page for b in blocks if is_annotatable(b)]
    return max(pages) if pages else 0


def filter_annotatable_annotations(
    blocks: list[PaperBlock],
    annotations: list[PaperAnnotation],
) -> list[PaperAnnotation]:
    """Drop annotations anchored on reference/back-matter blocks."""
    block_map = {b.block_id: b for b in blocks}
    ref_start = detect_reference_start_page(blocks)
    kept: list[PaperAnnotation] = []
    for ann in annotations:
        block = block_map.get(ann.target.block_id)
        if not block or not is_annotatable(block):
            continue
        if ref_start is not None and block.page >= ref_start:
            continue
        kept.append(ann)
    return kept
