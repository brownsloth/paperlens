from __future__ import annotations

import json
import re
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


def create_session_from_upload(filename: str, pdf_bytes: bytes) -> PaperDocument:
    if not pdf_bytes or pdf_bytes[:5] != b"%PDF-":
        raise ValueError("Uploaded file is not a valid PDF")

    paper_id = uuid.uuid4().hex[:12]
    session_dir = PUBLIC_SESSIONS_DIR / paper_id
    session_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = session_dir / "source.pdf"
    pdf_path.write_bytes(pdf_bytes)

    title = _title_from_filename(filename)
    doc = parse_paper(
        pdf_path,
        paper_id=paper_id,
        title=title,
        force=True,
    )
    meta = {
        "paper_id": paper_id,
        "title": title,
        "filename": filename,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "public": True,
    }
    _session_meta_path(paper_id).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return doc


def public_pdf_path(paper_id: str) -> Path | None:
    if not is_public_session(paper_id):
        return None
    path = PUBLIC_SESSIONS_DIR / paper_id / "source.pdf"
    return path if path.exists() else None
