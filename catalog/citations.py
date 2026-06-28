from __future__ import annotations

import re
import uuid

from catalog.store import MISC_ID, add_document, ensure_seeded
from paperlens.annotate import load_parsed
from paperlens.arxiv import download_arxiv_pdf, fetch_arxiv_metadata
from paperlens.paths import PAPERS_MANIFEST, PAPERS_RAW_DIR
from paperlens.sections import block_zone

ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([\w./-]+?)(?:\.pdf)?(?:\s|$|[\])>,])", re.I)
ARXIV_ID_RE = re.compile(r"\barXiv:\s*([\w./-]+)", re.I)
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\])>,]+)", re.I)


def extract_citations(paper_id: str) -> list[dict]:
    doc = load_parsed(paper_id)
    if not doc:
        return []

    seen: set[str] = set()
    citations: list[dict] = []

    ref_start = None
    if doc.metadata:
        ref_start = doc.metadata.get("reference_start_page")

    for block in doc.blocks:
        zone = block_zone(block)
        in_refs = zone == "references" or (
            ref_start is not None and block.page >= int(ref_start)
        )
        if not in_refs and block.block_type.value != "list_item":
            continue
        text = block.text.strip()
        if len(text) < 12:
            continue

        arxiv_id = _extract_arxiv_id(text)
        doi = _extract_doi(text)
        key = arxiv_id or doi or text[:80]
        if key in seen:
            continue
        seen.add(key)

        citations.append(
            {
                "citation_id": f"cite_{uuid.uuid4().hex[:8]}",
                "text": text[:500],
                "block_id": block.block_id,
                "page": block.page,
                "arxiv_id": arxiv_id,
                "doi": doi,
                "downloadable": bool(arxiv_id),
            }
        )
    return citations[:200]


def _extract_arxiv_id(text: str) -> str | None:
    m = ARXIV_URL_RE.search(text)
    if m:
        return m.group(1).rstrip("/")
    m = ARXIV_ID_RE.search(text)
    if m:
        return m.group(1)
    return None


def _extract_doi(text: str) -> str | None:
    m = DOI_RE.search(text)
    return m.group(1).rstrip(".,;") if m else None


def fetch_citation_to_misc(*, arxiv_id: str | None = None, doi: str | None = None) -> dict:
    """Download open-access paper (arXiv) into misc category."""
    ensure_seeded()
    if not arxiv_id and doi:
        arxiv_id = _doi_to_arxiv(doi)
    if not arxiv_id:
        raise ValueError("Only arXiv citations can be auto-downloaded. DOI requires manual upload.")

    meta = fetch_arxiv_metadata(arxiv_id)
    paper_id = _paper_id_from_arxiv(arxiv_id)
    pdf_path = PAPERS_RAW_DIR / f"{paper_id}.pdf"
    download_arxiv_pdf(arxiv_id, pdf_path)

    entry = {
        "paper_id": paper_id,
        "arxiv_id": arxiv_id,
        "title": meta["title"],
        "authors": meta["authors"],
        "year": meta["year"],
        "abstract": meta["abstract"],
        "pdf_path": str(pdf_path),
        "pdf_status": "available",
        "source": "arxiv",
        "category_id": MISC_ID,
    }
    _merge_paper_manifest(entry)
    doc = add_document(
        category_id=MISC_ID,
        kind="paper",
        title=meta["title"],
        paper_id=paper_id,
        arxiv_id=arxiv_id,
    )
    return {"paper": entry, "document": doc}


def _paper_id_from_arxiv(arxiv_id: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", arxiv_id.lower()).strip("-")
    return f"misc-{safe}"[:64]


def _merge_paper_manifest(entry: dict) -> None:
    import json
    import time

    manifest = {"papers": []}
    if PAPERS_MANIFEST.exists():
        manifest = json.loads(PAPERS_MANIFEST.read_text(encoding="utf-8"))
    papers = [p for p in manifest.get("papers", []) if p["paper_id"] != entry["paper_id"]]
    papers.append(entry)
    manifest["papers"] = papers
    manifest["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    PAPERS_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _doi_to_arxiv(doi: str) -> str | None:
    """Best-effort: some DOIs map to arXiv via API."""
    import httpx

    try:
        resp = httpx.get(
            f"https://api.crossref.org/works/{doi}",
            headers={"User-Agent": "PaperLens/0.1"},
            timeout=30,
        )
        if resp.status_code != 200:
            return None
        message = resp.json().get("message", {})
        for link in message.get("link", []):
            url = link.get("URL", "")
            m = ARXIV_URL_RE.search(url)
            if m:
                return m.group(1)
        for alt in message.get("alternative-id", []):
            if isinstance(alt, str) and alt.replace(".", "").isdigit():
                continue
    except Exception:
        return None
    return None
