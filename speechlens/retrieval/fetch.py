from __future__ import annotations

from dataclasses import dataclass

import httpx
import trafilatura

from speechlens.config import settings


@dataclass
class RetrievedChunk:
    title: str
    url: str
    excerpt: str
    source_type: str


def fetch_page_excerpt(url: str, *, max_chars: int | None = None) -> RetrievedChunk | None:
    max_chars = max_chars or settings.max_source_excerpt_chars
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            downloaded = _fetch_with_httpx(url)
        if not downloaded:
            return None
        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
        if not text:
            return None
        metadata = trafilatura.extract_metadata(downloaded)
        title = metadata.title if metadata and metadata.title else url
        return RetrievedChunk(
            title=title,
            url=url,
            excerpt=text[:max_chars],
            source_type=_source_type(url),
        )
    except Exception:
        return None


def _fetch_with_httpx(url: str) -> str | None:
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": "SpeechLens/0.1"})
            response.raise_for_status()
            return response.text
    except Exception:
        return None


def _source_type(url: str) -> str:
    lower = url.lower()
    if any(m in lower for m in ("blog", "medium.com", "substack")):
        return "expert_blog"
    if any(m in lower for m in ("archive.org", "loc.gov", "edu", "blackpast.org")):
        return "archive"
    return "web"
