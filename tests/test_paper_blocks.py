from __future__ import annotations

from pathlib import Path

import pytest

from paperlens.chunking.structure import build_annotation_candidates
from paperlens.models import BBox, BlockType, PaperBlock
from paperlens.parse.pdf_blocks import extract_blocks_from_pdf
from paperlens.resolve import attach_bbox_to_annotations, bbox_to_overlay, resolve_quote_span
from paperlens.models import AnnotationTarget, PaperAnnotation, PaperAnnotationType


@pytest.fixture
def malcolm_pdf() -> Path:
    path = Path(__file__).resolve().parents[1] / "data" / "raw" / "MalcolmX.pdf"
    if not path.exists():
        pytest.skip("MalcolmX.pdf not present")
    return path


def test_extract_blocks_has_bboxes(malcolm_pdf: Path) -> None:
    blocks = extract_blocks_from_pdf(str(malcolm_pdf), "test_paper")
    assert len(blocks) > 5
    block = blocks[0]
    assert block.bbox.x1 > block.bbox.x0
    assert block.page >= 1
    assert block.block_id.startswith("p")


def test_structure_chunks_skip_tiny_blocks() -> None:
    blocks = [
        PaperBlock(
            block_id="p01_b001",
            paper_id="p",
            page=1,
            block_type=BlockType.PARAGRAPH,
            text="Short.",
            bbox=BBox(x0=0, y0=0, x1=100, y1=20),
            reading_order=1,
            section="Introduction",
        ),
        PaperBlock(
            block_id="p01_b002",
            paper_id="p",
            page=1,
            block_type=BlockType.PARAGRAPH,
            text="A" * 120,
            bbox=BBox(x0=0, y0=30, x1=100, y1=60),
            reading_order=2,
            section="Introduction",
        ),
    ]
    chunks = build_annotation_candidates(blocks, max_candidates=5)
    assert len(chunks) == 1
    assert chunks[0].block_ids == ["p01_b002"]


def test_resolve_quote_span() -> None:
    block = PaperBlock(
        block_id="p02_b001",
        paper_id="p",
        page=2,
        block_type=BlockType.PARAGRAPH,
        text="The constant error carousel enables long credit paths.",
        bbox=BBox(x0=10, y0=10, x1=200, y1=40),
        reading_order=1,
    )
    start, end = resolve_quote_span(block, "constant error carousel")
    assert start == 4
    assert end == 27


def test_attach_bbox_to_annotations() -> None:
    block = PaperBlock(
        block_id="p02_b001",
        paper_id="p",
        page=2,
        block_type=BlockType.PARAGRAPH,
        text="Hello world",
        bbox=BBox(x0=10, y0=10, x1=200, y1=40),
        reading_order=1,
    )
    ann = PaperAnnotation(
        annotation_id="ann_1",
        paper_id="p",
        target=AnnotationTarget(block_id="p02_b001", quote="world"),
        annotation_type=PaperAnnotationType.CONCEPT_EXPLANATION,
        annotation_text="test",
    )
    resolved = attach_bbox_to_annotations([block], [ann])
    assert resolved[0].page == 2
    assert resolved[0].bbox is not None


def test_bbox_to_overlay_scaling() -> None:
    from paperlens.models import PageInfo

    page = PageInfo(
        page=1,
        image_path="x.png",
        width_px=612,
        height_px=792,
        pdf_width=612,
        pdf_height=792,
    )
    overlay = bbox_to_overlay(BBox(x0=0, y0=0, x1=100, y1=50), 612, 792, 612.0, 792.0)
    assert overlay["width"] == pytest.approx(100)
    assert overlay["height"] == pytest.approx(50)
