from __future__ import annotations

import json
import re
import shutil
import time
import uuid
from pathlib import Path

from paperlens.annotate import load_annotated, load_parsed, parse_paper
from paperlens.models import PaperDocument
from paperlens.paths import DATA_DIR

PUBLIC_SESSIONS_DIR = DATA_DIR / "public_sessions"
PUBLIC_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _session_meta_path(paper_id: str) -> Path:
    return PUBLIC_SESSIONS_DIR / paper_id / "session.json"


def load_session_meta(paper_id: str) -> dict:
    path = _session_meta_path(paper_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_session_meta(paper_id: str, meta: dict) -> None:
    _session_meta_path(paper_id).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def get_llm_call_count(paper_id: str) -> int:
    return int(load_session_meta(paper_id).get("llm_calls", 0))


def get_annotation_chat_count(paper_id: str, annotation_id: str) -> int:
    chats = load_session_meta(paper_id).get("annotation_chats", {})
    return int(chats.get(annotation_id, 0))


def record_llm_usage(paper_id: str, *, annotation_id: str | None = None) -> None:
    meta = load_session_meta(paper_id)
    meta["llm_calls"] = int(meta.get("llm_calls", 0)) + 1
    if annotation_id:
        chats = dict(meta.get("annotation_chats", {}))
        chats[annotation_id] = int(chats.get(annotation_id, 0)) + 1
        meta["annotation_chats"] = chats
    save_session_meta(paper_id, meta)


def delete_public_session(paper_id: str) -> None:
    session_dir = PUBLIC_SESSIONS_DIR / paper_id
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)


def is_public_session(paper_id: str) -> bool:
    return _session_meta_path(paper_id).exists()


def list_public_sessions() -> list[str]:
    ids: list[str] = []
    if not PUBLIC_SESSIONS_DIR.exists():
        return ids
    for path in PUBLIC_SESSIONS_DIR.iterdir():
        if path.is_dir() and _session_meta_path(path.name).exists():
            ids.append(path.name)
    return ids


def get_public_paper(paper_id: str) -> PaperDocument | None:
    if not is_public_session(paper_id):
        return None
    return load_annotated(paper_id) or load_parsed(paper_id)


def _title_from_filename(filename: str) -> str:
    stem = Path(filename).stem.replace("_", " ").replace("-", " ")
    return stem.strip() or "Uploaded paper"


def create_session_from_upload(
    filename: str,
    pdf_bytes: bytes,
    *,
    max_pages: int | None = None,
) -> PaperDocument:
    if not pdf_bytes or pdf_bytes[:5] != b"%PDF-":
        raise ValueError("Uploaded file is not a valid PDF")

    paper_id = uuid.uuid4().hex[:12]
    session_dir = PUBLIC_SESSIONS_DIR / paper_id
    session_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = session_dir / "source.pdf"
    pdf_path.write_bytes(pdf_bytes)

    title = _title_from_filename(filename)
    try:
        doc = parse_paper(
            pdf_path,
            paper_id=paper_id,
            title=title,
            force=True,
        )
        if max_pages is not None and doc.paper.page_count > max_pages:
            raise ValueError(
                f"PDF has too many pages ({doc.paper.page_count}; max {max_pages} on the public demo)."
            )
    except Exception:
        delete_public_session(paper_id)
        raise

    meta = {
        "paper_id": paper_id,
        "title": title,
        "filename": filename,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "public": True,
        "llm_calls": 0,
        "annotation_chats": {},
    }
    save_session_meta(paper_id, meta)
    return doc


def public_pdf_path(paper_id: str) -> Path | None:
    if not is_public_session(paper_id):
        return None
    path = PUBLIC_SESSIONS_DIR / paper_id / "source.pdf"
    return path if path.exists() else None
