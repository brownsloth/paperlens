from __future__ import annotations

from pathlib import Path

import pymupdf

from paperlens.models import BlockType, PaperBlock
from paperlens.paths import PAPER_FIGURES_DIR


def attach_figure_crops(
    doc: pymupdf.Document,
    blocks: list[PaperBlock],
    paper_id: str,
) -> list[PaperBlock]:
    """Save PNG crops for figure/image blocks."""
    out_dir = PAPER_FIGURES_DIR / paper_id
    out_dir.mkdir(parents=True, exist_ok=True)
    updated: list[PaperBlock] = []

    for block in blocks:
        if block.block_type != BlockType.FIGURE:
            updated.append(block)
            continue
        page = doc[block.page - 1]
        rect = pymupdf.Rect(block.bbox.x0, block.bbox.y0, block.bbox.x1, block.bbox.y1)
        if rect.width < 8 or rect.height < 8:
            updated.append(block)
            continue
        pix = page.get_pixmap(clip=rect, alpha=False)
        crop_path = out_dir / f"{block.block_id}.png"
        pix.save(str(crop_path))
        updated.append(block.model_copy(update={"image_crop_path": str(crop_path)}))

    return updated
