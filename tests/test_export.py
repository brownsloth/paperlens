from pathlib import Path

import pymupdf as fitz

from paperlens.export import export_annotated_pdf, export_markdown, _pdf_plain_text
from paperlens.models import (
    AnnotationTarget,
    BBox,
    PaperAnnotation,
    PaperAnnotationType,
    PaperBlock,
    PaperChatMessage,
    PaperDocument,
    PaperMeta,
    BlockType,
)


def test_export_markdown_includes_annotations():
    doc = PaperDocument(
        paper=PaperMeta(
            paper_id="test",
            title="Test Paper",
            authors=["A. Author"],
            year=2024,
            pdf_status="available",
            page_count=1,
            block_count=1,
            has_annotations=True,
        ),
        blocks=[],
        pages=[],
        annotations=[
            PaperAnnotation(
                annotation_id="ann_1",
                paper_id="test",
                target=AnnotationTarget(block_id="b1", quote="selected text"),
                annotation_type="concept_explanation",
                annotation_text="This is a note.",
                lens="beginner",
                page=2,
            )
        ],
    )
    md = export_markdown(doc)
    assert "Test Paper" in md
    assert "selected text" in md
    assert "This is a note." in md
    assert "Page 2" in md


def test_export_annotated_pdf_embeds_highlight(tmp_path: Path):
    pdf_path = tmp_path / "source.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello annotated world")
    doc.save(pdf_path)
    doc.close()

    paper = PaperDocument(
        paper=PaperMeta(
            paper_id="test",
            title="Test Paper",
            authors=[],
            pdf_status="available",
            page_count=1,
            block_count=1,
            has_annotations=True,
        ),
        blocks=[
            PaperBlock(
                block_id="b1",
                paper_id="test",
                page=1,
                block_type=BlockType.PARAGRAPH,
                text="Hello annotated world",
                bbox=BBox(x0=72, y0=60, x1=300, y1=90),
                reading_order=1,
            )
        ],
        pages=[],
        annotations=[
            PaperAnnotation(
                annotation_id="ann_1",
                paper_id="test",
                target=AnnotationTarget(block_id="b1", quote="Hello"),
                annotation_type=PaperAnnotationType.HIGHLIGHT,
                annotation_text="Hello",
                lens="beginner",
                evidence_status="highlight",
                page=1,
                bbox=BBox(x0=72, y0=60, x1=200, y1=90),
            )
        ],
    )

    out = export_annotated_pdf(paper, pdf_path)
    assert out[:5] == b"%PDF-"
    annotated = fitz.open(stream=out, filetype="pdf")
    try:
        assert len(list(annotated[0].annots())) >= 1
    finally:
        annotated.close()


def test_pdf_plain_text_strips_markdown_and_latex():
    raw = "### Title\n\n1. **Block** \\( \\bar{z}^t \\):\n   - \\( x^t \\) and σ"
    plain = _pdf_plain_text(raw)
    assert "###" not in plain
    assert "**" not in plain
    assert "\\bar" not in plain
    assert "Block" in plain
    assert "sigma" in plain
    assert "(" not in plain and ")" not in plain


def test_export_pdf_note_popups_are_unique(tmp_path: Path):
    pdf_path = tmp_path / "source.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 200), "First block")
    page.insert_text((72, 400), "Second block")
    page.insert_text((72, 600), "Third block")
    doc.save(pdf_path)
    doc.close()

    paper = PaperDocument(
        paper=PaperMeta(
            paper_id="test",
            title="Popup Test",
            authors=[],
            pdf_status="available",
            page_count=1,
            block_count=3,
            has_annotations=True,
        ),
        blocks=[],
        pages=[],
        annotations=[
            PaperAnnotation(
                annotation_id="ann_1",
                paper_id="test",
                target=AnnotationTarget(block_id="b1", quote="First"),
                annotation_type=PaperAnnotationType.CONCEPT_EXPLANATION,
                annotation_text="First note body.",
                lens="beginner",
                page=1,
                bbox=BBox(x0=72, y0=180, x1=300, y1=220),
            ),
            PaperAnnotation(
                annotation_id="ann_2",
                paper_id="test",
                target=AnnotationTarget(block_id="b2", quote="Second"),
                annotation_type=PaperAnnotationType.CONCEPT_EXPLANATION,
                annotation_text="Second note body.",
                lens="beginner",
                page=1,
                bbox=BBox(x0=72, y0=380, x1=300, y1=420),
            ),
            PaperAnnotation(
                annotation_id="ann_3",
                paper_id="test",
                target=AnnotationTarget(block_id="b3", quote="Third block text"),
                annotation_type=PaperAnnotationType.CONCEPT_EXPLANATION,
                annotation_text="Third note explains xt, N, and M variables.",
                lens="beginner",
                page=1,
                bbox=BBox(x0=72, y0=580, x1=300, y1=620),
            ),
        ],
    )

    out = export_annotated_pdf(paper, pdf_path)
    annotated = fitz.open(stream=out, filetype="pdf")
    try:
        page = annotated[0]
        notes = [a for a in page.annots(types=[fitz.PDF_ANNOT_TEXT])]
        assert len(notes) == 3
        popups = [tuple(round(v, 1) for v in a.popup_rect) for a in notes]
        assert len(set(popups)) == 3
        for a in notes:
            pr = a.popup_rect
            assert pr.width <= 285
            assert pr.height <= 145
            raw = annotated.xref_object(a.xref)
            assert "FEFF" not in raw  # ASCII literal encoding, not UTF-16
        third = notes[2]
        assert "Third note explains" in third.info["content"]
        xref_text = annotated.xref_object(third.xref)
        assert "/Contents" in xref_text
        assert xref_text.rstrip().endswith(">>")
    finally:
        annotated.close()


def test_export_lstm_figure_notes_use_compact_popups(tmp_path: Path):
    """Regression: long figure notes used 400px+ popups that Chrome would not show."""
    json_path = Path(__file__).resolve().parents[1] / "data/processed/papers/annotated/3b153d3cd67a.json"
    if not json_path.exists():
        return
    doc = PaperDocument.model_validate_json(json_path.read_text())
    src = next(Path(__file__).resolve().parents[1].joinpath("data").rglob("*.pdf"), None)
    if not src:
        return
    out = export_annotated_pdf(doc, src)
    annotated = fitz.open(stream=out, filetype="pdf")
    try:
        text_notes: list[tuple[fitz.Annot, fitz.Page]] = []
        for page in annotated:
            for a in page.annots(types=[fitz.PDF_ANNOT_TEXT]) or []:
                text_notes.append((a, page))
        assert len(text_notes) == 4
        for a, _page in text_notes:
            pr = a.popup_rect
            assert pr.height <= 145, f"popup too tall: {pr.height}"
            assert "FEFF" not in annotated.xref_object(a.xref)
            assert len(a.info["content"]) > 20
    finally:
        annotated.close()


def test_export_pdf_includes_annotation_thread(tmp_path: Path):
    pdf_path = tmp_path / "source.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    paper = PaperDocument(
        paper=PaperMeta(
            paper_id="test",
            title="Thread Test",
            authors=[],
            pdf_status="available",
            page_count=1,
            block_count=1,
            has_annotations=True,
        ),
        blocks=[],
        pages=[],
        annotations=[
            PaperAnnotation(
                annotation_id="ann_1",
                paper_id="test",
                target=AnnotationTarget(block_id="b1", quote="selected"),
                annotation_type=PaperAnnotationType.CONCEPT_EXPLANATION,
                annotation_text="Root explanation about LSTM gates.",
                lens="beginner",
                page=1,
                bbox=BBox(x0=72, y0=60, x1=300, y1=90),
                thread=[
                    PaperChatMessage(role="user", content="What is xt?"),
                    PaperChatMessage(
                        role="assistant",
                        content="xt is the input vector at timestep t.",
                    ),
                ],
            )
        ],
    )

    out = export_annotated_pdf(paper, pdf_path)
    annotated = fitz.open(stream=out, filetype="pdf")
    try:
        page = annotated[0]
        notes = [a for a in page.annots(types=[fitz.PDF_ANNOT_TEXT])]
        assert len(notes) == 1
        content = notes[0].info["content"]
        assert "Root explanation about LSTM gates." in content
        assert "Follow-up:" in content
        assert "What is xt?" in content
        assert "xt is the input vector at timestep t." in content
    finally:
        annotated.close()


def test_export_markdown_includes_annotation_thread():
    doc = PaperDocument(
        paper=PaperMeta(
            paper_id="test",
            title="Thread Test",
            authors=[],
            pdf_status="available",
            page_count=1,
            block_count=1,
            has_annotations=True,
        ),
        blocks=[],
        pages=[],
        annotations=[
            PaperAnnotation(
                annotation_id="ann_1",
                paper_id="test",
                target=AnnotationTarget(block_id="b1"),
                annotation_type="concept_explanation",
                annotation_text="Root note.",
                lens="beginner",
                page=1,
                thread=[
                    PaperChatMessage(role="user", content="Follow-up question?"),
                    PaperChatMessage(role="assistant", content="Follow-up answer."),
                ],
            )
        ],
    )
    md = export_markdown(doc)
    assert "Root note." in md
    assert "**You:** Follow-up question?" in md
    assert "**Assistant:** Follow-up answer." in md
