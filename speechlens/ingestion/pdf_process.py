from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Any

from speechlens.ingestion.speech_splitter import (
    SpeechEntry,
    build_speech_entries,
    extract_speech_text,
    format_speech_transcript,
)
from speechlens.paths import PROCESSED_DIR, SPEECHES_DIR


@dataclass
class SeedReport:
    source_id: str
    input_path: str
    backend: str
    speeches_found: int
    speeches_written: int
    output_dir: str
    speech_files: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "seeded_at": date.today().isoformat(),
        }


def get_seed_paths(source_id: str) -> dict[str, Path]:
    base = PROCESSED_DIR / source_id
    return {
        "manifest": base.with_suffix(".manifest.json"),
        "report": base.with_suffix(".seed.report.json"),
        "speeches_dir": SPEECHES_DIR / source_id,
    }


def seed_speeches_from_pdf(
    pdf_path: Path,
    *,
    source_id: str | None = None,
    backend: str = "pymupdf",
    ocr_engine: str = "auto",
    force: bool = False,
    limit: int | None = None,
) -> SeedReport:
    pdf_path = Path(pdf_path)
    source_id = source_id or slugify_stem(pdf_path.stem)
    paths = get_seed_paths(source_id)
    out_dir = paths["speeches_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    if paths["manifest"].exists() and not force:
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        return SeedReport(
            source_id=source_id,
            input_path=str(pdf_path),
            backend=backend,
            speeches_found=manifest["speeches_found"],
            speeches_written=manifest["speeches_written"],
            output_dir=str(out_dir),
            speech_files=manifest["speech_files"],
        )

    entries = build_speech_entries(pdf_path)
    if limit:
        entries = entries[:limit]

    speech_files: list[str] = []
    manifest_entries: list[dict[str, Any]] = []

    for entry in entries:
        text = extract_speech_text(
            pdf_path,
            entry,
            backend=backend,
            ocr_engine=ocr_engine,
        )
        if len(text) < 100:
            continue
        transcript = format_speech_transcript(entry.title, text)
        out_path = out_dir / f"{entry.slug}.txt"
        out_path.write_text(transcript, encoding="utf-8")
        speech_files.append(str(out_path.relative_to(PROCESSED_DIR.parent)))
        manifest_entries.append(
            {
                "title": entry.title,
                "slug": entry.slug,
                "start_page": entry.start_page,
                "end_page": entry.end_page,
                "file": out_path.name,
                "chars": len(transcript),
            }
        )

    manifest = {
        "source_id": source_id,
        "input_path": str(pdf_path),
        "backend": backend,
        "speeches_found": len(build_speech_entries(pdf_path)),
        "speeches_written": len(speech_files),
        "speech_files": speech_files,
        "entries": manifest_entries,
    }
    paths["manifest"].write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    report = SeedReport(
        source_id=source_id,
        input_path=str(pdf_path),
        backend=backend,
        speeches_found=manifest["speeches_found"],
        speeches_written=len(speech_files),
        output_dir=str(out_dir),
        speech_files=speech_files,
    )
    paths["report"].write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return report


def slugify_stem(stem: str) -> str:
    return stem.lower().replace(" ", "-")
