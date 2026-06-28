from __future__ import annotations

from pathlib import Path

import pymupdf

from paperlens.models import PageInfo
from paperlens.paths import PAPER_PAGES_DIR


def render_pdf_pages(
    pdf_path: str,
    paper_id: str,
    *,
    dpi: int = 144,
    force: bool = False,
) -> list[PageInfo]:
    out_dir = PAPER_PAGES_DIR / paper_id
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    pages: list[PageInfo] = []

    for page_idx, page in enumerate(doc, start=1):
        image_path = out_dir / f"page_{page_idx:03d}.png"
        if force or not image_path.exists():
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            pix.save(str(image_path))
        else:
            pix = page.get_pixmap(matrix=matrix, alpha=False)

        rect = page.rect
        pages.append(
            PageInfo(
                page=page_idx,
                image_path=str(image_path),
                width_px=pix.width,
                height_px=pix.height,
                pdf_width=float(rect.width),
                pdf_height=float(rect.height),
            )
        )

    doc.close()
    return pages
