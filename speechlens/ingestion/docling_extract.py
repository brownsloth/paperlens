from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

OcrEngine = Literal["auto", "off", "easyocr", "rapidocr"]


@dataclass
class DoclingResult:
    markdown: str
    latex: str
    source_path: str
    page_range: tuple[int, int] | None
    used_ocr: bool


def _build_converter(use_ocr: bool, ocr_engine: OcrEngine):
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions()
    opts.do_ocr = use_ocr
    opts.do_table_structure = False

    if use_ocr:
        if ocr_engine == "easyocr":
            from docling.datamodel.pipeline_options import EasyOcrOptions

            opts.ocr_options = EasyOcrOptions()
        elif ocr_engine == "rapidocr":
            from docling.datamodel.pipeline_options import RapidOcrOptions

            opts.ocr_options = RapidOcrOptions()

    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )


def extract_with_docling(
    pdf_path: Path,
    *,
    page_range: tuple[int, int] | None = None,
    ocr_engine: OcrEngine = "auto",
) -> DoclingResult:
    pdf_path = Path(pdf_path)
    use_ocr = ocr_engine not in ("auto", "off")
    if ocr_engine == "auto":
        use_ocr = False

    converter = _build_converter(use_ocr=use_ocr, ocr_engine=ocr_engine)
    kwargs: dict = {}
    if page_range is not None:
        kwargs["page_range"] = page_range

    result = converter.convert(str(pdf_path), **kwargs)
    doc = result.document
    markdown = doc.export_to_markdown().strip()

    latex = ""
    if hasattr(doc, "export_to_latex"):
        try:
            latex = doc.export_to_latex()
        except Exception:
            latex = ""

    return DoclingResult(
        markdown=markdown,
        latex=latex,
        source_path=str(pdf_path),
        page_range=page_range,
        used_ocr=use_ocr,
    )


def extract_text_from_pdf(
    pdf_path: Path,
    *,
    page_range: tuple[int, int] | None = None,
    ocr_engine: OcrEngine = "auto",
) -> str:
    return extract_with_docling(
        pdf_path,
        page_range=page_range,
        ocr_engine=ocr_engine,
    ).markdown
