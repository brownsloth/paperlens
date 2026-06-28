from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image

from paperlens.models import BBox, PageInfo
from paperlens.paths import PAPER_FIGURES_DIR, PAPER_PAGES_DIR


def crop_page_region(
    paper_id: str,
    page: int,
    bbox: BBox,
    page_info: PageInfo,
) -> Path:
    """Crop a PDF-coordinate region from a rendered page PNG."""
    src = PAPER_PAGES_DIR / paper_id / f"page_{page:03d}.png"
    if not src.exists():
        raise FileNotFoundError(f"Page image not found: {src}")

    scale_x = page_info.width_px / page_info.pdf_width
    scale_y = page_info.height_px / page_info.pdf_height
    x0 = max(0, int(bbox.x0 * scale_x))
    y0 = max(0, int(bbox.y0 * scale_y))
    x1 = min(page_info.width_px, int(bbox.x1 * scale_x))
    y1 = min(page_info.height_px, int(bbox.y1 * scale_y))
    if x1 <= x0 or y1 <= y0:
        raise ValueError("Selection region is too small")

    out_dir = PAPER_FIGURES_DIR / paper_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"sel_{uuid.uuid4().hex[:10]}.png"

    with Image.open(src) as img:
        cropped = img.crop((x0, y0, x1, y1))
        cropped.save(out_path)
    return out_path


def merge_bboxes(boxes: list[BBox]) -> BBox:
    return BBox(
        x0=min(b.x0 for b in boxes),
        y0=min(b.y0 for b in boxes),
        x1=max(b.x1 for b in boxes),
        y1=max(b.y1 for b in boxes),
    )


def pixel_rect_to_pdf_bbox(
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    page_info: PageInfo,
    container_width: float,
) -> BBox:
    """Convert a screen-space rect (relative to page container) to PDF points."""
    scale = container_width / page_info.width_px
    px_left = left / scale
    px_top = top / scale
    px_w = width / scale
    px_h = height / scale
    pdf_scale_x = page_info.pdf_width / page_info.width_px
    pdf_scale_y = page_info.pdf_height / page_info.height_px
    return BBox(
        x0=px_left * pdf_scale_x,
        y0=px_top * pdf_scale_y,
        x1=(px_left + px_w) * pdf_scale_x,
        y1=(px_top + px_h) * pdf_scale_y,
    )
