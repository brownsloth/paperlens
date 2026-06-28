from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import httpx

from paperlens.paths import PAPERS_MANIFEST, PAPERS_RAW_DIR

ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_PDF = "https://arxiv.org/pdf/{arxiv_id}.pdf"
REQUEST_DELAY_SEC = 3.0
SCHMIDHUBER_RE = re.compile(r"schmidhuber", re.I)
USER_AGENT = "PaperLens/0.1 (research corpus tool; mailto:local@paperlens.dev)"
STARTER_IDS: set[str] = set()


@dataclass(frozen=True)
class StarterPaper:
    paper_id: str
    arxiv_id: str
    title_hint: str


# Verified arXiv IDs with Juergen Schmidhuber as author.
STARTER_PAPERS: list[StarterPaper] = [
    StarterPaper("deep-learning-overview-2014", "1404.7828", "Deep Learning in Neural Networks"),
    StarterPaper("compression-curiosity-2008", "0812.4360", "Driven by Compression Progress"),
    StarterPaper("creativity-theory-2007", "0709.0674", "Simple Algorithmic Principles of Discovery"),
    StarterPaper("godel-machine-2003", "cs/0309048", "Goedel Machines"),
    StarterPaper("powerplay-2011", "1112.5309", "POWERPLAY"),
    StarterPaper("oops-2002", "cs/0207097", "Optimal Ordered Problem Solver"),
    StarterPaper("lstm-survey-2015", "1503.04069", "LSTM: A Search Space Odyssey"),
    StarterPaper("deep-learning-timeline-2013", "1312.5548", "My First Deep Learning System"),
    StarterPaper("clockwork-rnn-2014", "1402.3511", "A Clockwork RNN"),
    StarterPaper("powerplay-experiments-2012", "1210.8385", "First Experiments with PowerPlay"),
    StarterPaper("blstm-phoneme-2008", "0804.3269", "Phoneme recognition in TIMIT with BLSTM-CTC"),
    StarterPaper("linear-transformers-2021", "2102.11174", "Linear Transformers Are Secretly Fast Weight Programmers"),
    StarterPaper("fast-weights-learning-2020", "2011.07831", "Learning Associative Inference Using Fast Weight Memory"),
    StarterPaper("world-models-2018", "1803.10122", "World Models"),
    StarterPaper("on-learning-to-think-2015", "1511.09249", "On Learning to Think"),
]

STARTER_IDS = {p.paper_id for p in STARTER_PAPERS}


def _is_schmidhuber_paper(authors: list[str]) -> bool:
    return any(SCHMIDHUBER_RE.search(a) for a in authors)


def _http_client() -> httpx.Client:
    return httpx.Client(
        timeout=120,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


def fetch_arxiv_metadata(arxiv_id: str) -> dict:
    time.sleep(REQUEST_DELAY_SEC)
    params = {"id_list": arxiv_id, "max_results": 1}
    with _http_client() as client:
        resp = client.get(ARXIV_API, params=params)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    entry = root.find("atom:entry", ARXIV_NS)
    if entry is None:
        raise ValueError(f"No arXiv metadata for {arxiv_id}")

    title = (entry.findtext("atom:title", default="", namespaces=ARXIV_NS) or "").strip()
    summary = (entry.findtext("atom:summary", default="", namespaces=ARXIV_NS) or "").strip()
    authors = [
        (a.findtext("atom:name", default="", namespaces=ARXIV_NS) or "").strip()
        for a in entry.findall("atom:author", ARXIV_NS)
    ]
    published = entry.findtext("atom:published", default="", namespaces=ARXIV_NS) or ""
    year = int(published[:4]) if len(published) >= 4 else None
    return {
        "arxiv_id": arxiv_id,
        "title": " ".join(title.split()),
        "abstract": summary,
        "authors": [a for a in authors if a],
        "year": year,
    }


def _is_valid_pdf(content: bytes) -> bool:
    return len(content) > 10_000 and content[:5] == b"%PDF-"


def download_arxiv_pdf(arxiv_id: str, dest: Path, *, force: bool = False) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not force and dest.exists() and dest.stat().st_size > 10_000:
        if dest.read_bytes()[:5] == b"%PDF-":
            return dest

    url = ARXIV_PDF.format(arxiv_id=arxiv_id)
    last_error: Exception | None = None
    for attempt in range(3):
        time.sleep(REQUEST_DELAY_SEC if attempt == 0 else REQUEST_DELAY_SEC * 2)
        try:
            with _http_client() as client:
                resp = client.get(url)
            if resp.status_code == 404:
                raise FileNotFoundError(f"arXiv PDF not found: {arxiv_id}")
            resp.raise_for_status()
            if not _is_valid_pdf(resp.content):
                raise ValueError(f"Downloaded file is not a valid PDF for {arxiv_id}")
            dest.write_bytes(resp.content)
            return dest
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Failed to download {arxiv_id} after retries") from last_error


def _merge_manifest_entries(existing: list[dict], new_entries: list[dict]) -> list[dict]:
    by_id = {e["paper_id"]: e for e in existing}
    for entry in new_entries:
        by_id[entry["paper_id"]] = entry
    return list(by_id.values())


def _remove_stale_pdfs(keep_ids: set[str]) -> None:
    if not PAPERS_RAW_DIR.exists():
        return
    for pdf in PAPERS_RAW_DIR.glob("*.pdf"):
        paper_id = pdf.stem
        if paper_id not in keep_ids:
            pdf.unlink(missing_ok=True)


def fetch_starter_papers(
    *,
    limit: int | None = None,
    force: bool = False,
) -> list[dict]:
    """Download verified Schmidhuber papers from arXiv. Merges into corpus manifest."""
    existing = load_manifest().get("papers", [])
    entries: list[dict] = []
    papers = STARTER_PAPERS[:limit] if limit else STARTER_PAPERS

    for starter in papers:
        try:
            meta = fetch_arxiv_metadata(starter.arxiv_id)
        except Exception as exc:
            entries.append(
                {
                    "paper_id": starter.paper_id,
                    "arxiv_id": starter.arxiv_id,
                    "title": starter.title_hint,
                    "pdf_status": "metadata_failed",
                    "error": str(exc),
                }
            )
            continue

        if not _is_schmidhuber_paper(meta["authors"]):
            entries.append(
                {
                    "paper_id": starter.paper_id,
                    "arxiv_id": starter.arxiv_id,
                    "title": meta["title"],
                    "authors": meta["authors"],
                    "pdf_status": "author_mismatch",
                    "error": "arXiv ID does not list Schmidhuber as author",
                }
            )
            continue

        pdf_path = PAPERS_RAW_DIR / f"{starter.paper_id}.pdf"
        try:
            download_arxiv_pdf(starter.arxiv_id, pdf_path, force=force)
            pdf_status = "available" if pdf_path.exists() else "missing"
        except Exception as exc:
            entries.append(
                {
                    "paper_id": starter.paper_id,
                    "arxiv_id": starter.arxiv_id,
                    "title": meta["title"],
                    "authors": meta["authors"],
                    "year": meta["year"],
                    "abstract": meta["abstract"],
                    "pdf_status": "download_failed",
                    "error": str(exc),
                }
            )
            continue

        entries.append(
            {
                "paper_id": starter.paper_id,
                "arxiv_id": starter.arxiv_id,
                "title": meta["title"],
                "authors": meta["authors"],
                "year": meta["year"],
                "abstract": meta["abstract"],
                "pdf_path": str(pdf_path),
                "pdf_status": pdf_status,
                "source": "arxiv",
            }
        )

    merged = _merge_manifest_entries(existing, entries)
    merged = [e for e in merged if e.get("pdf_status") == "available"]
    _remove_stale_pdfs({e["paper_id"] for e in merged})
    manifest = {"papers": merged, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    PAPERS_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return entries


def download_url_pdf(url: str, dest: Path, *, force: bool = False) -> Path:
    """Download a PDF from an arbitrary URL (OpenReview, PMC, etc.)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not force and dest.exists() and dest.stat().st_size > 10_000:
        if dest.read_bytes()[:5] == b"%PDF-":
            return dest

    last_error: Exception | None = None
    for attempt in range(3):
        time.sleep(REQUEST_DELAY_SEC if attempt == 0 else REQUEST_DELAY_SEC * 2)
        try:
            with _http_client() as client:
                resp = client.get(url)
            if resp.status_code == 404:
                raise FileNotFoundError(f"PDF not found: {url}")
            resp.raise_for_status()
            if not _is_valid_pdf(resp.content):
                raise ValueError(f"Downloaded file is not a valid PDF from {url}")
            dest.write_bytes(resp.content)
            return dest
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Failed to download {url} after retries") from last_error


def fetch_corpus_papers(
    papers: list,
    *,
    force: bool = False,
) -> list[dict]:
    """Download curated corpus papers. Merges into manifest without pruning other PDFs."""
    from paperlens.corpora.real_world_learning import CorpusPaper

    existing = load_manifest().get("papers", [])
    entries: list[dict] = []

    for spec in papers:
        if not isinstance(spec, CorpusPaper):
            raise TypeError(f"Expected CorpusPaper, got {type(spec)}")

        meta: dict = {
            "title": spec.title_hint,
            "authors": list(spec.authors),
            "year": spec.year,
            "corpus": "real-world-learning",
        }
        if spec.arxiv_id:
            meta["arxiv_id"] = spec.arxiv_id
        if spec.doi:
            meta["doi"] = spec.doi

        if spec.arxiv_id:
            try:
                arxiv_meta = fetch_arxiv_metadata(spec.arxiv_id)
                meta.update(
                    {
                        "title": arxiv_meta["title"],
                        "authors": arxiv_meta["authors"],
                        "year": arxiv_meta["year"],
                        "abstract": arxiv_meta["abstract"],
                    }
                )
            except Exception as exc:
                entries.append(
                    {
                        "paper_id": spec.paper_id,
                        **meta,
                        "pdf_status": "metadata_failed",
                        "error": str(exc),
                    }
                )
                continue

        pdf_path = PAPERS_RAW_DIR / f"{spec.paper_id}.pdf"
        if spec.arxiv_id:
            try:
                download_arxiv_pdf(spec.arxiv_id, pdf_path, force=force)
                entries.append(
                    {
                        "paper_id": spec.paper_id,
                        **meta,
                        "pdf_path": str(pdf_path),
                        "pdf_status": "available",
                        "source": "arxiv",
                    }
                )
            except Exception as exc:
                entries.append(
                    {
                        "paper_id": spec.paper_id,
                        **meta,
                        "pdf_status": "download_failed",
                        "error": str(exc),
                    }
                )
            continue

        if spec.pdf_url:
            try:
                download_url_pdf(spec.pdf_url, pdf_path, force=force)
                entries.append(
                    {
                        "paper_id": spec.paper_id,
                        **meta,
                        "pdf_path": str(pdf_path),
                        "pdf_status": "available",
                        "source": "url",
                        "pdf_url": spec.pdf_url,
                    }
                )
            except Exception as exc:
                entries.append(
                    {
                        "paper_id": spec.paper_id,
                        **meta,
                        "pdf_status": "download_failed",
                        "error": str(exc),
                        "pdf_url": spec.pdf_url,
                    }
                )
            continue

        entries.append(
            {
                "paper_id": spec.paper_id,
                **meta,
                "pdf_status": "metadata_only",
            }
        )

    merged = _merge_manifest_entries(existing, entries)
    manifest = {"papers": merged, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    PAPERS_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return entries


def fetch_real_world_learning_papers(*, force: bool = False) -> list[dict]:
    from paperlens.corpora.real_world_learning import REAL_WORLD_LEARNING_PAPERS

    return fetch_corpus_papers(REAL_WORLD_LEARNING_PAPERS, force=force)


def load_manifest() -> dict:
    if not PAPERS_MANIFEST.exists():
        return {"papers": []}
    return json.loads(PAPERS_MANIFEST.read_text(encoding="utf-8"))
