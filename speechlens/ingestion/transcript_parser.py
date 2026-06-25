from __future__ import annotations

import re
import uuid
from pathlib import Path

import trafilatura

from speechlens.models import Segment, Transcript


SPEAKER_PATTERN = re.compile(
    r"^(?P<speaker>[A-Z][A-Za-z .'\-]+):\s*(?P<text>.*)$",
    re.MULTILINE,
)


def _new_doc_id() -> str:
    return f"doc_{uuid.uuid4().hex[:12]}"


def _new_segment_id(index: int) -> str:
    return f"seg_{index:04d}"


def parse_transcript_text(
    text: str,
    *,
    title: str | None = None,
    source_url: str | None = None,
    date: str | None = None,
) -> Transcript:
    text = text.strip()
    if not text:
        raise ValueError("Transcript text is empty")

    segments: list[Segment] = []
    speakers: set[str] = set()
    matches = list(SPEAKER_PATTERN.finditer(text))

    if matches:
        for idx, match in enumerate(matches):
            speaker = match.group("speaker").strip()
            speakers.add(speaker)
            start = match.end("speaker") + 2
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            segment_text = text[start:end].strip()
            if segment_text:
                segments.append(
                    Segment(
                        segment_id=_new_segment_id(len(segments) + 1),
                        speaker=speaker,
                        text=segment_text,
                    )
                )
    else:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        for paragraph in paragraphs:
            segments.append(
                Segment(
                    segment_id=_new_segment_id(len(segments) + 1),
                    text=paragraph,
                )
            )

    return Transcript(
        doc_id=_new_doc_id(),
        title=title or "Untitled Speech",
        date=date,
        source_url=source_url,
        speakers=sorted(speakers),
        segments=segments,
    )


def load_text_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_pdf_file(path: str | Path) -> str:
    import fitz

    doc = fitz.open(path)
    pages = [page.get_text() for page in doc]
    return "\n\n".join(pages).strip()


def load_url(url: str) -> tuple[str, str | None]:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError(f"Could not fetch URL: {url}")
    extracted = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    if not extracted:
        raise ValueError(f"Could not extract text from URL: {url}")
    metadata = trafilatura.extract_metadata(downloaded)
    title = metadata.title if metadata else None
    return extracted, title
