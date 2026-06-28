from paperlens.annotate import load_annotated, load_parsed
from paperlens.arxiv import load_manifest
from paperlens.models import PaperDocument, PaperMeta
from paperlens.paths import PAPERS_RAW_DIR


def _manifest_entry(paper_id: str) -> dict | None:
    manifest = load_manifest()
    return next((e for e in manifest.get("papers", []) if e["paper_id"] == paper_id), None)


def _stub_document(entry: dict) -> PaperDocument:
    paper_id = entry["paper_id"]
    return PaperDocument(
        paper=PaperMeta(
            paper_id=paper_id,
            title=entry.get("title", paper_id),
            authors=entry.get("authors", []),
            year=entry.get("year"),
            arxiv_id=entry.get("arxiv_id"),
            abstract=entry.get("abstract"),
            pdf_path=entry.get("pdf_path"),
            pdf_status=entry.get("pdf_status", "unknown"),
            source=entry.get("source", "arxiv"),
        ),
        blocks=[],
        pages=[],
        annotations=[],
    )


def list_papers() -> list[PaperMeta]:
    manifest = load_manifest()
    papers: list[PaperMeta] = []
    for entry in manifest.get("papers", []):
        if entry.get("pdf_status") != "available":
            continue
        paper_id = entry["paper_id"]
        parsed = load_annotated(paper_id) or load_parsed(paper_id)
        if parsed:
            papers.append(parsed.paper)
            continue
        papers.append(_stub_document(entry).paper)
    return papers


def get_paper(paper_id: str) -> PaperDocument | None:
    doc = load_annotated(paper_id) or load_parsed(paper_id)
    if doc:
        return doc
    entry = _manifest_entry(paper_id)
    if entry and entry.get("pdf_status") == "available":
        return _stub_document(entry)
    return None


def get_pdf_path(paper_id: str) -> str | None:
    doc = get_paper(paper_id)
    if doc and doc.paper.pdf_path:
        return doc.paper.pdf_path
    entry = _manifest_entry(paper_id)
    if entry:
        path = entry.get("pdf_path")
        if path:
            return path
    candidate = PAPERS_RAW_DIR / f"{paper_id}.pdf"
    if candidate.exists():
        return str(candidate)
    return None
