from __future__ import annotations

import re

import pymupdf

from paperlens.models import BBox, BlockType, PaperBlock
from paperlens.parse.figures import attach_figure_crops
from paperlens.sections import assign_zones

_HEADING_RE = re.compile(
    r"^(abstract|introduction|background|related work|method|methods|"
    r"experiments?|results?|discussion|conclusion|references|appendix)\b",
    re.I,
)
_CAPTION_RE = re.compile(r"^(figure|fig\.|table)\s*\d+", re.I)
_REF_LINE_RE = re.compile(r"^\[\d+\]|^\d+\.\s+[A-Z]")


def _extract_lines(block: dict) -> list[dict]:
    lines_out: list[dict] = []
    for line in block.get("lines") or []:
        parts: list[str] = []
        for span in line.get("spans") or []:
            parts.append(span.get("text") or "")
        text = "".join(parts).strip()
        bbox_raw = line.get("bbox")
        if not text or not bbox_raw:
            continue
        lines_out.append(
            {
                "text": text,
                "bbox": {
                    "x0": float(bbox_raw[0]),
                    "y0": float(bbox_raw[1]),
                    "x1": float(bbox_raw[2]),
                    "y1": float(bbox_raw[3]),
                },
            }
        )
    return lines_out


def _block_text(block: dict) -> tuple[str, float | None]:
    lines = block.get("lines") or []
    parts: list[str] = []
    sizes: list[float] = []
    for line in lines:
        for span in line.get("spans") or []:
            t = span.get("text") or ""
            if t:
                parts.append(t)
                size = span.get("size")
                if size:
                    sizes.append(float(size))
        parts.append("\n")
    text = "".join(parts).strip()
    avg_size = sum(sizes) / len(sizes) if sizes else None
    return text, avg_size


def _classify_block(text: str, font_size: float | None, median_size: float) -> BlockType:
    if not text:
        return BlockType.OTHER
    if _CAPTION_RE.match(text):
        return BlockType.CAPTION
    if _HEADING_RE.match(text) and len(text) < 120:
        return BlockType.HEADING
    if font_size and font_size > median_size * 1.15 and len(text) < 100:
        return BlockType.HEADING
    if len(text) < 200 and sum(c in text for c in "=∑∫∂√±×") >= 2:
        return BlockType.EQUATION
    if _REF_LINE_RE.match(text) and len(text) < 300:
        return BlockType.LIST_ITEM
    return BlockType.PARAGRAPH


def extract_blocks_from_pdf(pdf_path: str, paper_id: str) -> list[PaperBlock]:
    doc = pymupdf.open(pdf_path)
    raw_sizes: list[float] = []
    raw_blocks: list[tuple[int, int, dict, str, float | None, int]] = []

    for page_idx, page in enumerate(doc, start=1):
        page_dict = page.get_text("dict")
        for block_idx, block in enumerate(page_dict.get("blocks") or []):
            block_type_num = block.get("type")
            if block_type_num == 1:
                bbox_raw = block["bbox"]
                raw_blocks.append(
                    (page_idx, block_idx, block, "", None, 1),
                )
                continue
            if block_type_num != 0:
                continue
            text, font_size = _block_text(block)
            if not text or len(text) < 2:
                continue
            raw_sizes.append(font_size or 12.0)
            raw_blocks.append((page_idx, block_idx, block, text, font_size, 0))

    median_size = sorted(raw_sizes)[len(raw_sizes) // 2] if raw_sizes else 12.0
    section = "Unknown"
    blocks: list[PaperBlock] = []
    order = 0

    for page_idx, block_idx, block, text, font_size, kind in raw_blocks:
        if kind == 1:
            bbox_raw = block["bbox"]
            bbox = BBox(x0=bbox_raw[0], y0=bbox_raw[1], x1=bbox_raw[2], y1=bbox_raw[3])
            order += 1
            blocks.append(
                PaperBlock(
                    block_id=f"p{page_idx:02d}_img{block_idx:03d}",
                    paper_id=paper_id,
                    page=page_idx,
                    block_type=BlockType.FIGURE,
                    text="",
                    bbox=bbox,
                    reading_order=order,
                    section=section,
                )
            )
            continue

        block_type = _classify_block(text, font_size, median_size)
        if block_type == BlockType.HEADING:
            section = text.strip().title()
        bbox_raw = block["bbox"]
        bbox = BBox(x0=bbox_raw[0], y0=bbox_raw[1], x1=bbox_raw[2], y1=bbox_raw[3])
        order += 1
        line_meta = _extract_lines(block)
        blocks.append(
            PaperBlock(
                block_id=f"p{page_idx:02d}_b{block_idx:03d}",
                paper_id=paper_id,
                page=page_idx,
                block_type=block_type,
                text=text,
                bbox=bbox,
                reading_order=order,
                section=section,
                font_size=font_size,
                metadata={"lines": line_meta} if line_meta else {},
            )
        )

    _link_captions(blocks)
    blocks = assign_zones(blocks)
    blocks = attach_figure_crops(doc, blocks, paper_id)
    doc.close()
    return blocks


def _link_captions(blocks: list[PaperBlock]) -> None:
    by_page: dict[int, list[PaperBlock]] = {}
    for block in blocks:
        by_page.setdefault(block.page, []).append(block)

    for page_blocks in by_page.values():
        figures = [b for b in page_blocks if b.block_type == BlockType.FIGURE]
        for block in page_blocks:
            if block.block_type != BlockType.CAPTION:
                continue
            if not figures:
                continue
            nearest = min(
                figures,
                key=lambda f: abs((f.bbox.y0 + f.bbox.y1) / 2 - (block.bbox.y0 + block.bbox.y1) / 2),
            )
            block.linked_blocks.append(nearest.block_id)
            nearest.linked_blocks.append(block.block_id)
