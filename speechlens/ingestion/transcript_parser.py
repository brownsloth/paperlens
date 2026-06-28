from __future__ import annotations

import re
import uuid
from pathlib import Path

import trafilatura

from speechlens.models import Segment, Transcript

SPEAKER_LINE = re.compile(
    r"^(?P<speaker>[A-Z][A-Za-z .'\-()]+):\s*(?P<text>.*)$",
    re.MULTILINE,
)

# Embedded section title e.g. "A Declaration of Independence\n(March 12, 1964)"

def _new_doc_id() -> str:
    return f"doc_{uuid.uuid4().hex[:12]}"


def _new_segment_id(index: int) -> str:
    return f"seg_{index:04d}"


def has_speaker_turns(text: str) -> bool:
    return len(SPEAKER_LINE.findall(text)) >= 2


def _strip_markdown_title(text: str) -> tuple[str | None, str]:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        return lines[0][2:].strip(), "\n".join(lines[1:]).strip()
    return None, text


def _unwrap_erroneous_speaker_wrapper(text: str) -> str:
    """Remove a bogus top-level MALCOLM X: wrapper around labeled dialogue."""
    if re.match(r"^MALCOLM X:\s*\n", text, re.IGNORECASE):
        rest = re.sub(r"^MALCOLM X:\s*\n", "", text, count=1, flags=re.IGNORECASE)
        if has_speaker_turns(rest):
            return rest.strip()
    return text


def _split_embedded_sections(text: str) -> list[tuple[str | None, str]]:
    """Split combined documents (e.g. FBI interview + press conference)."""
    pattern = r"(?:^|\n)([A-Z][^\n:]{4,120})\n\(([^)]+)\)\s*\n"
    parts = re.split(pattern, text)
    if len(parts) == 1:
        return [(None, text.strip())]

    sections: list[tuple[str | None, str]] = []
    preamble = parts[0].strip()
    if preamble:
        sections.append((None, preamble))
    idx = 1
    while idx + 2 < len(parts):
        section_title = f"{parts[idx].strip()} ({parts[idx + 1].strip()})"
        body = parts[idx + 2].strip()
        sections.append((section_title, body))
        idx += 3
    return sections


def _parse_speaker_blocks(text: str) -> list[tuple[str, str]]:
    matches = list(SPEAKER_LINE.finditer(text))
    if not matches:
        return []

    blocks: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        speaker = match.group("speaker").strip()
        start = match.start("text")
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        segment_text = text[start:end].strip()
        if segment_text:
            blocks.append((speaker, segment_text))
    return blocks


def _parse_paragraph_blocks(text: str, *, default_speaker: str = "MALCOLM X") -> list[tuple[str, str]]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return [(default_speaker, paragraph) for paragraph in paragraphs]


def _parse_section(
    section_text: str,
    *,
    section_title: str | None,
    segments: list[Segment],
    speakers: set[str],
) -> None:
    section_text = section_text.strip()
    if not section_text:
        return

    default_speaker = "MALCOLM X"
    if section_title:
        default_speaker = "MALCOLM X"

    if has_speaker_turns(section_text):
        for speaker, segment_text in _parse_speaker_blocks(section_text):
            speakers.add(speaker)
            segments.append(
                Segment(
                    segment_id=_new_segment_id(len(segments) + 1),
                    speaker=speaker,
                    text=segment_text,
                )
            )
    else:
        for speaker, segment_text in _parse_paragraph_blocks(section_text, default_speaker=default_speaker):
            speakers.add(speaker)
            segments.append(
                Segment(
                    segment_id=_new_segment_id(len(segments) + 1),
                    speaker=speaker,
                    text=segment_text,
                )
            )


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

    file_title, text = _strip_markdown_title(text)
    if not title and file_title:
        title = file_title

    text = _unwrap_erroneous_speaker_wrapper(text)
    sections = _split_embedded_sections(text)

    segments: list[Segment] = []
    speakers: set[str] = set()

    if len(sections) == 1 and not sections[0][0]:
        only_text = sections[0][1]
        if has_speaker_turns(only_text):
            for speaker, segment_text in _parse_speaker_blocks(only_text):
                speakers.add(speaker)
                segments.append(
                    Segment(
                        segment_id=_new_segment_id(len(segments) + 1),
                        speaker=speaker,
                        text=segment_text,
                    )
                )
        else:
            for speaker, segment_text in _parse_paragraph_blocks(only_text):
                speakers.add(speaker)
                segments.append(
                    Segment(
                        segment_id=_new_segment_id(len(segments) + 1),
                        speaker=speaker,
                        text=segment_text,
                    )
                )
    else:
        for section_title, section_text in sections:
            _parse_section(
                section_text,
                section_title=section_title,
                segments=segments,
                speakers=speakers,
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
    extracted_title = metadata.title if metadata else None
    return extracted, extracted_title
