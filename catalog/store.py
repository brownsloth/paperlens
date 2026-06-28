from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

from catalog.paths import CATEGORIES_PATH
from catalog.paths import PROCESSED_DIR
from paperlens.arxiv import load_manifest

MALCOLM_X_ID = "malcolm-x"
SCHMIDHUBER_ID = "jurgen-schmidhuber"
MISC_ID = "misc"
REAL_WORLD_LEARNING_ID = "real-world-learning"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _load() -> dict:
    if not CATEGORIES_PATH.exists():
        return {"categories": [], "documents": []}
    return json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    CATEGORIES_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def ensure_seeded() -> dict:
    data = _load()
    if data.get("categories"):
        return data

    categories = [
        {"id": MALCOLM_X_ID, "name": "Malcolm X"},
        {"id": SCHMIDHUBER_ID, "name": "Jürgen Schmidhuber"},
        {"id": MISC_ID, "name": "Misc"},
    ]
    documents: list[dict] = []

    mx_manifest = PROCESSED_DIR / "malcolmx.manifest.json"
    if mx_manifest.exists():
        manifest = json.loads(mx_manifest.read_text(encoding="utf-8"))
        for entry in manifest.get("entries", []):
            slug = entry["slug"]
            documents.append(
                {
                    "doc_id": f"speech:malcolmx:{slug}",
                    "category_id": MALCOLM_X_ID,
                    "kind": "speech",
                    "title": entry["title"],
                    "source_id": "malcolmx",
                    "slug": slug,
                }
            )

    paper_manifest = load_manifest()
    for entry in paper_manifest.get("papers", []):
        if entry.get("pdf_status") != "available":
            continue
        pid = entry["paper_id"]
        documents.append(
            {
                "doc_id": f"paper:{pid}",
                "category_id": SCHMIDHUBER_ID,
                "kind": "paper",
                "title": entry.get("title", pid),
                "paper_id": pid,
                "arxiv_id": entry.get("arxiv_id"),
            }
        )

    data = {"categories": categories, "documents": documents}
    _save(data)
    return data


def ensure_real_world_learning_category() -> dict:
    """Create Real World Learning category and link all corpus papers."""
    from paperlens.corpora.real_world_learning import CORPUS_NAME, REAL_WORLD_LEARNING_IDS

    data = ensure_seeded()
    if not any(c["id"] == REAL_WORLD_LEARNING_ID for c in data["categories"]):
        data["categories"].append({"id": REAL_WORLD_LEARNING_ID, "name": CORPUS_NAME})

    manifest = load_manifest()
    added = 0
    for entry in manifest.get("papers", []):
        pid = entry["paper_id"]
        if pid not in REAL_WORLD_LEARNING_IDS:
            continue
        doc_id = f"paper:{pid}"
        doc = {
            "doc_id": doc_id,
            "category_id": REAL_WORLD_LEARNING_ID,
            "kind": "paper",
            "title": entry.get("title", pid),
            "paper_id": pid,
            "arxiv_id": entry.get("arxiv_id"),
            "doi": entry.get("doi"),
            "pdf_status": entry.get("pdf_status"),
        }
        existing = next((d for d in data["documents"] if d["doc_id"] == doc_id), None)
        if existing:
            existing.update(doc)
        else:
            data["documents"].append(doc)
            added += 1

    _save(data)
    return {"category_id": REAL_WORLD_LEARNING_ID, "added": added, "total": len(REAL_WORLD_LEARNING_IDS)}


def list_categories() -> list[dict]:
    data = ensure_seeded()
    docs = data.get("documents", [])
    out: list[dict] = []
    for cat in data.get("categories", []):
        cat_docs = [d for d in docs if d.get("category_id") == cat["id"]]
        out.append({**cat, "document_count": len(cat_docs)})
    return out


def list_documents(category_id: str, *, search: str = "") -> list[dict]:
    data = ensure_seeded()
    docs = [d for d in data.get("documents", []) if d.get("category_id") == category_id]
    q = search.strip().lower()
    if not q:
        return docs
    return [
        d
        for d in docs
        if q in d.get("title", "").lower()
        or q in (d.get("slug") or "").lower()
        or q in (d.get("paper_id") or "").lower()
        or q in (d.get("arxiv_id") or "").lower()
    ]


def create_category(name: str) -> dict:
    data = ensure_seeded()
    cat_id = _SLUG_RE.sub("-", name.strip().lower()).strip("-") or f"cat-{uuid.uuid4().hex[:8]}"
    if any(c["id"] == cat_id for c in data["categories"]):
        cat_id = f"{cat_id}-{uuid.uuid4().hex[:6]}"
    cat = {"id": cat_id, "name": name.strip()}
    data["categories"].append(cat)
    _save(data)
    return cat


def add_document(
    *,
    category_id: str,
    kind: str,
    title: str,
    source_id: str | None = None,
    slug: str | None = None,
    paper_id: str | None = None,
    arxiv_id: str | None = None,
) -> dict:
    data = ensure_seeded()
    if kind == "speech":
        doc_id = f"speech:{source_id}:{slug}"
    else:
        doc_id = f"paper:{paper_id}"
    if any(d["doc_id"] == doc_id for d in data["documents"]):
        for d in data["documents"]:
            if d["doc_id"] == doc_id:
                d["category_id"] = category_id
                _save(data)
                return d
    doc = {
        "doc_id": doc_id,
        "category_id": category_id,
        "kind": kind,
        "title": title,
        "source_id": source_id,
        "slug": slug,
        "paper_id": paper_id,
        "arxiv_id": arxiv_id,
    }
    data["documents"].append(doc)
    _save(data)
    return doc


def move_document(doc_id: str, category_id: str) -> dict:
    data = ensure_seeded()
    for doc in data["documents"]:
        if doc["doc_id"] == doc_id:
            doc["category_id"] = category_id
            _save(data)
            return doc
    raise FileNotFoundError(f"Document not found: {doc_id}")


def get_document(doc_id: str) -> dict | None:
    data = ensure_seeded()
    return next((d for d in data["documents"] if d["doc_id"] == doc_id), None)


def search_category(category_id: str, query: str) -> list[dict]:
    """Search titles and shallow full-text in speeches/papers."""
    from paperlens.annotate import load_annotated, load_parsed
    from speechlens.library import load_speech

    q = query.strip().lower()
    if not q:
        return list_documents(category_id)

    hits: list[dict] = []
    for doc in list_documents(category_id):
        if _doc_matches_query(doc, q):
            hits.append({**doc, "match": "title"})
            continue
        snippet = _snippet_for_doc(doc, q)
        if snippet:
            hits.append({**doc, "match": "content", "snippet": snippet})
    return hits


def _doc_matches_query(doc: dict, q: str) -> bool:
    fields = [doc.get("title", ""), doc.get("slug", ""), doc.get("paper_id", ""), doc.get("arxiv_id", "")]
    return any(q in (f or "").lower() for f in fields)


def _snippet_for_doc(doc: dict, q: str) -> str | None:
    try:
        if doc["kind"] == "speech":
            from speechlens.library import load_speech

            speech = load_speech(doc["source_id"], doc["slug"])
            text = " ".join(s.text for s in speech.segments)
            idx = text.lower().find(q)
            if idx < 0:
                return None
            return text[max(0, idx - 40) : idx + len(q) + 60].strip()
        paper = None
        from paperlens.annotate import load_annotated, load_parsed

        pid = doc["paper_id"]
        paper_doc = load_annotated(pid) or load_parsed(pid)
        if not paper_doc:
            return None
        for block in paper_doc.blocks:
            if q in block.text.lower():
                i = block.text.lower().find(q)
                return block.text[max(0, i - 40) : i + len(q) + 60].strip()
        for ann in paper_doc.annotations:
            if q in ann.annotation_text.lower():
                return ann.annotation_text[:120]
    except Exception:
        return None
    return None


def search_paper(paper_id: str, query: str) -> dict:
    from paperlens.annotate import load_annotated, load_parsed

    q = query.strip().lower()
    doc = load_annotated(paper_id) or load_parsed(paper_id)
    if not doc or not q:
        return {"blocks": [], "annotations": []}

    blocks = [
        {"block_id": b.block_id, "page": b.page, "text": b.text[:300], "snippet": _highlight_snippet(b.text, q)}
        for b in doc.blocks
        if q in b.text.lower()
    ][:40]
    annotations = [
        {
            "annotation_id": a.annotation_id,
            "page": a.page,
            "annotation_text": a.annotation_text,
            "quote": a.target.quote,
        }
        for a in doc.annotations
        if q in a.annotation_text.lower() or q in (a.target.quote or "").lower()
    ]
    return {"blocks": blocks, "annotations": annotations}


def _highlight_snippet(text: str, q: str) -> str:
    idx = text.lower().find(q)
    if idx < 0:
        return text[:160]
    return text[max(0, idx - 50) : idx + len(q) + 80].strip()
