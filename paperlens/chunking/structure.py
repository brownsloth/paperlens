from __future__ import annotations

from dataclasses import dataclass

from paperlens.models import BlockType, PaperBlock
from paperlens.sections import is_annotatable


@dataclass
class PaperChunk:
    chunk_id: str
    paper_id: str
    block_ids: list[str]
    block_type: str
    text: str
    section: str | None
    page: int
    annotation_question: str
    image_crop_path: str | None = None


def build_annotation_candidates(
    blocks: list[PaperBlock],
    *,
    max_candidates: int = 20,
) -> list[PaperChunk]:
    """Pick structure-aware chunks worth annotating; excludes references/back matter."""
    annotatable = [b for b in blocks if is_annotatable(b)]
    chunks: list[PaperChunk] = []
    paragraph_buffer: list[PaperBlock] = []

    def flush_paragraphs() -> None:
        nonlocal paragraph_buffer
        if not paragraph_buffer:
            return
        usable = [b for b in paragraph_buffer if len(b.text) >= 40]
        if not usable:
            paragraph_buffer = []
            return
        text = "\n\n".join(b.text for b in usable)
        if len(text) < 80:
            paragraph_buffer = []
            return
        block = usable[0]
        chunks.append(
            PaperChunk(
                chunk_id=f"chunk_{block.block_id}",
                paper_id=block.paper_id,
                block_ids=[b.block_id for b in usable],
                block_type="paragraph",
                text=text[:2500],
                section=block.section,
                page=block.page,
                annotation_question=f"What is the main idea in this {block.section or 'section'} passage?",
            )
        )
        paragraph_buffer = []

    for block in annotatable:
        if block.block_type == BlockType.HEADING:
            flush_paragraphs()
            continue
        if block.block_type == BlockType.PARAGRAPH:
            if paragraph_buffer and paragraph_buffer[-1].page != block.page:
                flush_paragraphs()
            paragraph_buffer.append(block)
            if sum(len(b.text) for b in paragraph_buffer) > 1200:
                flush_paragraphs()
            continue
        flush_paragraphs()
        if block.block_type == BlockType.EQUATION:
            chunks.append(
                PaperChunk(
                    chunk_id=f"chunk_{block.block_id}",
                    paper_id=block.paper_id,
                    block_ids=[block.block_id],
                    block_type="equation",
                    text=block.text,
                    section=block.section,
                    page=block.page,
                    annotation_question="What does this equation mean intuitively, term by term?",
                    image_crop_path=block.image_crop_path,
                )
            )
        elif block.block_type == BlockType.FIGURE and block.image_crop_path:
            chunks.append(
                PaperChunk(
                    chunk_id=f"chunk_{block.block_id}",
                    paper_id=block.paper_id,
                    block_ids=[block.block_id, *block.linked_blocks],
                    block_type="figure",
                    text=block.text,
                    section=block.section,
                    page=block.page,
                    annotation_question="What is this figure showing and why does it matter?",
                    image_crop_path=block.image_crop_path,
                )
            )
        elif block.block_type == BlockType.CAPTION:
            chunks.append(
                PaperChunk(
                    chunk_id=f"chunk_{block.block_id}",
                    paper_id=block.paper_id,
                    block_ids=[block.block_id, *block.linked_blocks],
                    block_type="caption",
                    text=block.text,
                    section=block.section,
                    page=block.page,
                    annotation_question="What is this figure/table showing and why does it matter?",
                )
            )

    flush_paragraphs()

    scored = sorted(
        chunks,
        key=lambda c: (
            0 if c.block_type in ("equation", "figure", "caption") else 1,
            c.page,
        ),
    )
    return scored[:max_candidates]
