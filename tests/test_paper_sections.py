from __future__ import annotations

from paperlens.models import BBox, BlockType, PaperBlock
from paperlens.sections import (
    annotatable_blocks,
    assign_zones,
    body_page_count,
    detect_reference_start_page,
    filter_annotatable_annotations,
    is_annotatable,
)


def _block(text: str, page: int, block_type: BlockType = BlockType.PARAGRAPH) -> PaperBlock:
    return PaperBlock(
        block_id=f"p{page:02d}_b001",
        paper_id="test",
        page=page,
        block_type=block_type,
        text=text,
        bbox=BBox(x0=0, y0=0, x1=100, y1=20),
        reading_order=page,
        section="Introduction",
    )


def test_reference_section_excluded_from_annotatable() -> None:
    blocks = [
        _block("Main idea about LSTM.", 5),
        PaperBlock(
            block_id="p35_b001",
            paper_id="test",
            page=35,
            block_type=BlockType.HEADING,
            text="References",
            bbox=BBox(x0=0, y0=0, x1=100, y1=20),
            reading_order=10,
            section="References",
        ),
        _block("[1] Hochreiter S., Schmidhuber J. (1997).", 36, BlockType.LIST_ITEM),
    ]
    zoned = assign_zones(blocks)
    assert detect_reference_start_page(zoned) == 35
    assert len(annotatable_blocks(zoned)) == 1
    assert body_page_count(zoned) == 5


def test_filter_annotatable_annotations() -> None:
    blocks = [
        _block("Main idea about LSTM.", 5),
        _block("[1] Hochreiter S., Schmidhuber J. (1997).", 36, BlockType.LIST_ITEM),
    ]
    zoned = assign_zones(blocks)
    from paperlens.models import AnnotationTarget, PaperAnnotation, PaperAnnotationType

    annotations = [
        PaperAnnotation(
            annotation_id="ann_a",
            paper_id="test",
            target=AnnotationTarget(block_id="p05_b001"),
            annotation_type=PaperAnnotationType.CONCEPT_EXPLANATION,
            annotation_text="Good note",
        ),
        PaperAnnotation(
            annotation_id="ann_b",
            paper_id="test",
            target=AnnotationTarget(block_id="p36_b001"),
            annotation_type=PaperAnnotationType.CITATION_CONTEXT,
            annotation_text="Should drop",
        ),
    ]
    filtered = filter_annotatable_annotations(zoned, annotations)
    assert len(filtered) == 1
    assert filtered[0].annotation_id == "ann_a"


def test_tail_reference_heuristic() -> None:
    blocks = [_block(f"Body paragraph {i} with enough content to pass filters.", i) for i in range(1, 31)]
    for page in range(31, 41):
        blocks.append(
            _block(f"[{page}] Author A., Author B. (199{page % 10}). Journal name.", page, BlockType.LIST_ITEM)
        )
    zoned = assign_zones(blocks)
    assert detect_reference_start_page(zoned) is not None
    assert all(not is_annotatable(b) for b in zoned if b.page >= 31)
