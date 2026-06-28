from __future__ import annotations

import re
from urllib.parse import urlparse

from speechlens.retrieval.fetch import RetrievedChunk
from speechlens.retrieval.search import SearchHit

# Hard-block: never pass these to the evidence scorer / writer
BLOCKED_DOMAIN_FRAGMENTS = (
    "translate.google",
    "imdb.com",
    "shiksha.com",
    "coursera.org/learn",
    "quizlet.com",
    "brainly.com",
    "chegg.com",
    "pinterest.",
    "facebook.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "amazon.com/dp",
    "goodreads.com/work",
    "sparknotes.com",
    "gradesaver.com",
)

BLOCKED_TITLE_PATTERNS = re.compile(
    r"\b(civil engineering|mechanical engineering|course catalog|worksheet|"
    r"flashcards|homework help|seo|buy essay)\b",
    re.I,
)

# Boost ranking for trusted source types
PREFERRED_DOMAIN_FRAGMENTS = (
    "loc.gov",
    "blackpast.org",
    "britannica.com",
    "stanford.edu",
    "yale.edu",
    "columbia.edu",
    "harvard.edu",
    "archive.org",
    "jstor.org",
    "gov",
    ".edu",
    "democracynow.org",
    "pbs.org",
    "npr.org",
    "smithsonian",
    "nationalarchives",
    "martin luther king",  # title heuristic
)


def is_blocked_source(url: str, title: str = "") -> bool:
    lower_url = url.lower()
    lower_title = title.lower()
    if any(b in lower_url for b in BLOCKED_DOMAIN_FRAGMENTS):
        return True
    if BLOCKED_TITLE_PATTERNS.search(lower_title):
        return True
    # Block single-word title pages that cause "human" → IMDb Human
    if lower_title.strip() in {"human", "rights", "front", "islam"}:
        return True
    return False


def source_quality_score(url: str, title: str = "") -> float:
    if is_blocked_source(url, title):
        return 0.0
    lower_url = url.lower()
    lower_title = title.lower()
    score = 0.4
    if any(p in lower_url for p in PREFERRED_DOMAIN_FRAGMENTS):
        score += 0.35
    if any(
        kw in lower_title
        for kw in ("malcolm x", "civil rights", "nation of islam", "speech", "transcript")
    ):
        score += 0.15
    if "wikipedia.org" in lower_url:
        score += 0.1
    if "blog" in lower_url or "medium.com" in lower_url or "substack" in lower_url:
        score += 0.05
    return min(score, 1.0)


def filter_search_hits(hits: list[SearchHit]) -> list[SearchHit]:
    filtered = [h for h in hits if not is_blocked_source(h.url, h.title)]
    return sorted(filtered, key=lambda h: source_quality_score(h.url, h.title), reverse=True)


def filter_retrieved_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    filtered = [c for c in chunks if not is_blocked_source(c.url, c.title)]
    return sorted(filtered, key=lambda c: source_quality_score(c.url, c.title), reverse=True)


def domain_label(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return url
