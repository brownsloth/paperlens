from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pymupdf as fitz

from paperlens.models import PaperAnnotation, PaperAnnotationType, PaperChatMessage, PaperDocument
from paperlens.storage import DEFAULT_HIGHLIGHT_COLOR, DEFAULT_NOTE_COLOR

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
_ASCII_REPLACEMENTS = {
    "\u03c3": "sigma",  # σ
    "\u2299": "*",  # ⊙
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
}

# Browsers (Chrome PDF) fail to show sticky-note popups that span most of the page.
_PDF_POPUP_WIDTH = 280.0
_PDF_POPUP_HEIGHT = 140.0
_PDF_NOTE_MAX_CHARS = 1200
_PDF_NOTE_WITH_THREAD_MAX_CHARS = 2800


def _annotation_kind(ann: PaperAnnotation) -> str:
    if ann.annotation_type == PaperAnnotationType.HIGHLIGHT:
        return "Highlight"
    if ann.evidence_status == "highlight":
        return "Highlight"
    if ann.evidence_status == "user_authored":
        return "Note"
    return "Annotation"


def _is_highlight(ann: PaperAnnotation) -> bool:
    return ann.annotation_type == PaperAnnotationType.HIGHLIGHT or ann.evidence_status == "highlight"


def _hex_to_rgb(hex_color: str, *, default: str) -> tuple[float, float, float]:
    raw = (hex_color or default).strip()
    match = _HEX_RE.match(raw)
    if not match:
        match = _HEX_RE.match(default)
    assert match
    value = int(match.group(1), 16)
    return ((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255


def _note_body(ann: PaperAnnotation) -> str:
    body = ann.annotation_text.strip()
    quote = (ann.target.quote or "").strip()
    if not body:
        return ""
    if quote and body == quote:
        return ""
    if quote and body.startswith(quote):
        rest = body[len(quote) :].strip()
        return rest
    return body


def _thread_role_label(msg: PaperChatMessage) -> str:
    return "You" if msg.role == "user" else "Assistant"


def _export_note_text(ann: PaperAnnotation) -> str:
    """Root annotation plus any user/assistant follow-up thread."""
    parts: list[str] = []
    root = _note_body(ann)
    if root:
        parts.append(root)
    thread_lines = [
        f"{_thread_role_label(msg)}: {msg.content.strip()}"
        for msg in ann.thread
        if msg.content.strip()
    ]
    if thread_lines:
        parts.extend(["---", "Follow-up:", *thread_lines])
    return "\n\n".join(parts)


def _pdf_plain_text(text: str, *, max_chars: int = _PDF_NOTE_MAX_CHARS) -> str:
    """Strip markdown/LaTeX and coerce to PDF-safe ASCII for sticky-note popups."""
    t = text.strip()
    if not t:
        return ""
    for src, dst in _ASCII_REPLACEMENTS.items():
        t = t.replace(src, dst)
    t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"__([^_]+)__", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\\[()[\]]", "", t)
    t = t.replace("\\", "")
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = unicodedata.normalize("NFKD", t)
    t = t.encode("ascii", "ignore").decode("ascii")
    # Literal parentheses in PDF strings are fragile in some viewers.
    t = t.replace("(", "[").replace(")", "]")
    if len(t) > max_chars:
        t = t[: max_chars - 3].rstrip() + "..."
    return t


def _popup_rect_for_note(page: fitz.Page, icon_rect: fitz.Rect) -> fitz.Rect:
    """Fixed-size popup beside the icon — oversized popups break Chrome's PDF viewer."""
    bounds = page.rect
    popup_w = min(_PDF_POPUP_WIDTH, bounds.width - 16.0)
    popup_h = min(_PDF_POPUP_HEIGHT, bounds.height - 16.0)

    x0 = icon_rect.x1 + 8.0
    if x0 + popup_w > bounds.x1 - 8.0:
        x0 = max(bounds.x0 + 8.0, icon_rect.x0 - popup_w - 8.0)

    y0 = icon_rect.y0 - 4.0
    if y0 + popup_h > bounds.y1 - 8.0:
        y0 = max(bounds.y0 + 8.0, icon_rect.y1 - popup_h + 4.0)

    return fitz.Rect(x0, y0, x0 + popup_w, y0 + popup_h)


def export_markdown(doc: PaperDocument) -> str:
    lines: list[str] = [
        f"# {doc.paper.title}",
        "",
    ]
    if doc.paper.authors:
        lines.append(f"**Authors:** {', '.join(doc.paper.authors)}")
    if doc.paper.year:
        lines.append(f"**Year:** {doc.paper.year}")
    if doc.paper.arxiv_id:
        lines.append(f"**arXiv:** {doc.paper.arxiv_id}")
    lines.extend(["", "---", "", "## Annotations", ""])

    if not doc.annotations:
        lines.append("_No annotations yet._")
    else:
        by_page: dict[int, list[PaperAnnotation]] = {}
        for ann in doc.annotations:
            page = ann.page or 0
            by_page.setdefault(page, []).append(ann)
        for page in sorted(by_page):
            lines.append(f"### Page {page}")
            lines.append("")
            for ann in by_page[page]:
                kind = _annotation_kind(ann)
                quote = (ann.target.quote or "").strip()
                if quote:
                    lines.append(f"> {quote}")
                    lines.append("")
                lines.append(f"**{kind}** ({ann.annotation_type})")
                lines.append("")
                lines.append(ann.annotation_text.strip())
                lines.append("")
                for msg in ann.thread:
                    if not msg.content.strip():
                        continue
                    lines.append(f"**{_thread_role_label(msg)}:** {msg.content.strip()}")
                    lines.append("")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def export_json(doc: PaperDocument) -> str:
    return json.dumps(doc.model_dump(), indent=2)


def export_annotated_pdf(doc: PaperDocument, pdf_path: Path | str) -> bytes:
    """Burn highlights and note popups into a copy of the source PDF."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    pdf = fitz.open(path)
    try:
        for ann in doc.annotations:
            if not ann.page or not ann.bbox:
                continue
            page_idx = ann.page - 1
            if page_idx < 0 or page_idx >= pdf.page_count:
                continue
            page = pdf[page_idx]
            rect = fitz.Rect(ann.bbox.x0, ann.bbox.y0, ann.bbox.x1, ann.bbox.y1)
            if rect.is_empty or rect.is_infinite:
                continue

            default = DEFAULT_HIGHLIGHT_COLOR if _is_highlight(ann) else DEFAULT_NOTE_COLOR
            rgb = _hex_to_rgb(ann.color or default, default=default)

            mark = page.add_highlight_annot(rect)
            if mark:
                mark.set_colors(stroke=rgb)
                mark.set_opacity(0.45 if _is_highlight(ann) else 0.35)
                mark.update()

            if _is_highlight(ann):
                continue

            note_text = _export_note_text(ann)
            max_chars = _PDF_NOTE_WITH_THREAD_MAX_CHARS if ann.thread else _PDF_NOTE_MAX_CHARS
            content = _pdf_plain_text(note_text, max_chars=max_chars)
            if not content:
                continue
            title = ann.annotation_type.value.replace("_", " ").title()
            point = fitz.Point(ann.bbox.x1, ann.bbox.y0)
            note = page.add_text_annot(point, content)
            note.set_info(title=title, content=content)
            note.set_colors(stroke=rgb)
            note.set_popup(_popup_rect_for_note(page, note.rect))
            note.update()

        return pdf.tobytes(garbage=4, deflate=True)
    finally:
        pdf.close()


def write_annotated_pdf(doc: PaperDocument, pdf_path: Path | str, dest: Path | str) -> Path:
    out = Path(dest)
    out.write_bytes(export_annotated_pdf(doc, pdf_path))
    return out
