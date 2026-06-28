from __future__ import annotations

from dataclasses import dataclass

from speechlens.config import settings


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str
    source_type: str = "web"


def web_search(query: str, *, max_results: int | None = None) -> list[SearchHit]:
    max_results = max_results or settings.max_search_results
    if settings.tavily_api_key:
        return _search_tavily(query, max_results=max_results)
    return _search_duckduckgo(query, max_results=max_results)


def _search_duckduckgo(query: str, *, max_results: int) -> list[SearchHit]:
    try:
        from duckduckgo_search import DDGS

        hits: list[SearchHit] = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                url = item.get("href") or item.get("link") or ""
                if not url:
                    continue
                hits.append(
                    SearchHit(
                        title=item.get("title", url),
                        url=url,
                        snippet=item.get("body", item.get("snippet", "")),
                        source_type=_classify_source(url),
                    )
                )
        return hits
    except Exception:
        return []


def _search_tavily(query: str, *, max_results: int) -> list[SearchHit]:
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(query, max_results=max_results, include_raw_content=False)
        hits: list[SearchHit] = []
        for item in response.get("results", []):
            url = item.get("url", "")
            if not url:
                continue
            hits.append(
                SearchHit(
                    title=item.get("title", url),
                    url=url,
                    snippet=item.get("content", ""),
                    source_type=_classify_source(url),
                )
            )
        return hits
    except Exception:
        return []


def _classify_source(url: str) -> str:
    lower = url.lower()
    blog_markers = ("blog", "medium.com", "substack", "wordpress", "tumblr")
    archive_markers = ("archive.org", "loc.gov", "jstor", "edu", "gov", "blackpast.org")
    if any(m in lower for m in blog_markers):
        return "expert_blog"
    if any(m in lower for m in archive_markers):
        return "archive"
    if lower.endswith(".edu") or ".edu/" in lower:
        return "scholarly"
    return "web"
