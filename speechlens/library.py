from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from speechlens.ingestion.service import IngestionService
from speechlens.models import AnnotateResponse, Transcript
from speechlens.paths import ANNOTATED_DIR, PROCESSED_DIR, SPEECHES_DIR


def list_sources() -> list[dict]:
    sources: list[dict] = []
    for manifest_path in sorted(PROCESSED_DIR.glob("*.manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_id = manifest["source_id"]
        annotated_dir = ANNOTATED_DIR / source_id
        annotated_count = len(list(annotated_dir.glob("*.json"))) if annotated_dir.exists() else 0
        sources.append(
            {
                "source_id": source_id,
                "title": _source_title(source_id),
                "speeches_count": manifest.get("speeches_written", 0),
                "annotated_count": annotated_count,
                "input_path": manifest.get("input_path"),
            }
        )
    return sources


def list_speeches(source_id: str, *, search: str = "") -> list[dict]:
    manifest = _load_manifest(source_id)
    entries = manifest.get("entries", [])
    query = search.strip().lower()
    speeches: list[dict] = []
    annotated_dir = ANNOTATED_DIR / source_id

    for entry in entries:
        title = entry["title"]
        slug = entry["slug"]
        if query and query not in title.lower() and query not in slug.lower():
            continue
        json_path = annotated_dir / f"{slug}.json"
        speeches.append(
            {
                "slug": slug,
                "title": title,
                "chars": entry.get("chars", 0),
                "start_page": entry.get("start_page"),
                "end_page": entry.get("end_page"),
                "has_annotations": json_path.exists(),
            }
        )
    return speeches


def load_speech(source_id: str, slug: str) -> AnnotateResponse:
    annotated = _load_annotated(source_id, slug)
    if annotated:
        return annotated
    transcript = _load_transcript(source_id, slug)
    return _transcript_to_response(transcript, metadata={"seeded": True, "source_id": source_id})


def annotate_speech(
    source_id: str,
    slug: str,
    *,
    mode: str = "medium",
    require_sources: bool = True,
    enable_web_search: bool = True,
) -> AnnotateResponse:
    from speechlens.annotator import SpeechAnnotator
    from speechlens.models import AnnotationDepth

    transcript = _load_transcript(source_id, slug)
    annotator = SpeechAnnotator(
        mode=AnnotationDepth(mode),
        require_sources=require_sources,
        enable_web_search=enable_web_search,
    )
    result = annotator.annotate(transcript).response
    _save_annotated(source_id, slug, result)
    return result


def _source_title(source_id: str) -> str:
    titles = {"malcolmx": "Malcolm X — Collected Speeches (1960–1965)"}
    return titles.get(source_id, source_id.replace("-", " ").title())


def _load_manifest(source_id: str) -> dict:
    manifest_path = PROCESSED_DIR / f"{source_id}.manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Unknown source: {source_id}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _speech_path(source_id: str, slug: str) -> Path:
    path = SPEECHES_DIR / source_id / f"{slug}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Speech not found: {source_id}/{slug}")
    return path


def _load_transcript(source_id: str, slug: str) -> Transcript:
    path = _speech_path(source_id, slug)
    manifest = _load_manifest(source_id)
    title = slug.replace("-", " ").title()
    for entry in manifest.get("entries", []):
        if entry["slug"] == slug:
            title = entry["title"]
            break
    return IngestionService().from_file(path, title=title)


def _load_annotated(source_id: str, slug: str) -> AnnotateResponse | None:
    path = ANNOTATED_DIR / source_id / f"{slug}.json"
    if not path.exists():
        return None
    try:
        return AnnotateResponse.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError:
        # Stale annotation JSON (schema drift) — fall back to raw transcript.
        return None


def _save_annotated(source_id: str, slug: str, response: AnnotateResponse) -> None:
    out_dir = ANNOTATED_DIR / source_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}.json"
    path.write_text(response.model_dump_json(indent=2), encoding="utf-8")


def _transcript_to_response(transcript: Transcript, metadata: dict | None = None) -> AnnotateResponse:
    return AnnotateResponse(
        doc_id=transcript.doc_id,
        title=transcript.title,
        segments=transcript.segments,
        annotations=[],
        metadata=metadata or {},
    )
