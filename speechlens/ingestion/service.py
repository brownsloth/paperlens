from __future__ import annotations

from pathlib import Path

from speechlens.ingestion.transcript_parser import (
    load_pdf_file,
    load_text_file,
    load_url,
    parse_transcript_text,
)
from speechlens.models import Transcript


class IngestionService:
    def from_text(
        self,
        text: str,
        *,
        title: str | None = None,
        source_url: str | None = None,
        date: str | None = None,
    ) -> Transcript:
        return parse_transcript_text(text, title=title, source_url=source_url, date=date)

    def from_file(self, path: str | Path, *, title: str | None = None) -> Transcript:
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            text = load_pdf_file(path)
        elif suffix in {".txt", ".md"}:
            text = load_text_file(path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
        return self.from_text(text, title=title or path.stem.replace("_", " ").title())

    def from_url(self, url: str) -> Transcript:
        text, extracted_title = load_url(url)
        return self.from_text(text, title=extracted_title, source_url=url)
