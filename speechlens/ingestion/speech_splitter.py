from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

HEADER_PATTERNS = [
    re.compile(r"^Collected Speeches, Debates & Interviews.*$", re.I),
    re.compile(r"^Malcolm X - El-Hajj Malik El-Shabazz.*$", re.I),
    re.compile(r"^\d+\s*$"),
]


@dataclass
class SpeechEntry:
    title: str
    start_page: int  # 1-based
    end_page: int  # 1-based inclusive
    slug: str


def parse_page_range(pages: str | None) -> tuple[int, int] | None:
    if not pages:
        return None
    if "-" in pages:
        a, b = pages.split("-", 1)
        return (int(a.strip()), int(b.strip()))
    n = int(pages.strip())
    return (1, n)


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug[:80] or "speech"


def parse_toc_from_pdf(pdf_path: Path, *, toc_start: int = 7, toc_end: int = 20) -> list[tuple[str, int]]:
    doc = pymupdf.open(pdf_path)
    toc_text = "\n".join(doc[i - 1].get_text() for i in range(toc_start, min(toc_end, doc.page_count) + 1))

    entries: list[tuple[str, int]] = []
    for line in toc_text.splitlines():
        match = re.search(r"^(.+?)\.{3,}(\d+)\s*$", line.strip())
        if not match:
            continue
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        page = int(match.group(2))
        if title and not title.isdigit():
            entries.append((title, page))
    return entries


def build_speech_entries(pdf_path: Path) -> list[SpeechEntry]:
    toc = parse_toc_from_pdf(pdf_path)
    if not toc:
        raise ValueError(f"No TOC entries found in {pdf_path}")

    doc = pymupdf.open(pdf_path)
    last_page = doc.page_count
    seen_slugs: dict[str, int] = {}
    speeches: list[SpeechEntry] = []

    for idx, (title, start_page) in enumerate(toc):
        end_page = toc[idx + 1][1] - 1 if idx + 1 < len(toc) else last_page
        base_slug = slugify(title)
        count = seen_slugs.get(base_slug, 0)
        seen_slugs[base_slug] = count + 1
        slug = base_slug if count == 0 else f"{base_slug}-{count + 1}"
        speeches.append(
            SpeechEntry(title=title, start_page=start_page, end_page=end_page, slug=slug)
        )
    return speeches


def _clean_page_text(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if any(p.match(stripped) for p in HEADER_PATTERNS):
            continue
        lines.append(line.rstrip())
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_pages_pymupdf(pdf_path: Path, start_page: int, end_page: int) -> str:
    doc = pymupdf.open(pdf_path)
    parts: list[str] = []
    for page_num in range(start_page, min(end_page, doc.page_count) + 1):
        parts.append(doc[page_num - 1].get_text())
    return _clean_page_text("\n".join(parts))


def extract_speech_text(
    pdf_path: Path,
    entry: SpeechEntry,
    *,
    backend: str = "pymupdf",
    ocr_engine: str = "auto",
) -> str:
    if backend == "docling":
        from speechlens.ingestion.docling_extract import extract_text_from_pdf

        return extract_text_from_pdf(
            pdf_path,
            page_range=(entry.start_page, entry.end_page),
            ocr_engine=ocr_engine,  # type: ignore[arg-type]
        )
    return extract_pages_pymupdf(pdf_path, entry.start_page, entry.end_page)


def format_speech_transcript(title: str, body: str) -> str:
    body = body.strip()
    title_norm = re.sub(r"\s+", " ", title).strip().lower()
    lines = body.splitlines()
    while lines:
        line_norm = re.sub(r"\s+", " ", lines[0]).strip().lower()
        if not line_norm or line_norm in title_norm or title_norm.startswith(line_norm):
            lines.pop(0)
            continue
        break
    body = "\n".join(lines).strip()

    from speechlens.ingestion.transcript_parser import has_speaker_turns

    if has_speaker_turns(body):
        return f"# {title}\n\n{body}"
    if re.match(r"^(MALCOLM X|INTERVIEWER|MODERATOR|AUDIENCE)\s*:", body, re.I):
        return f"# {title}\n\n{body}"
    return f"# {title}\n\nMALCOLM X:\n{body}"
