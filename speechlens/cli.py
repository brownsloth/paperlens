from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from speechlens.annotator import SpeechAnnotator
from speechlens.ingestion.pdf_process import seed_speeches_from_pdf
from speechlens.models import AnnotationDepth
from speechlens.paths import ANNOTATED_DIR, DEFAULT_MALCOLM_PDF, SPEECHES_DIR

app = typer.Typer(help="SpeechLens: source-grounded speech annotation")
console = Console()


@app.command()
def annotate(
    text: Optional[str] = typer.Option(None, "--text", help="Raw transcript text"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Transcript file (.txt, .md, .pdf)"),
    url: Optional[str] = typer.Option(None, "--url", help="URL to extract transcript from"),
    mode: AnnotationDepth = typer.Option(AnnotationDepth.MEDIUM, "--mode", "-m"),
    out: Path = typer.Option(Path("annotated.md"), "--out", "-o", help="Output file path"),
    title: Optional[str] = typer.Option(None, "--title", help="Document title override"),
    require_sources: bool = typer.Option(True, "--require-sources/--no-require-sources"),
    no_web_search: bool = typer.Option(False, "--no-web-search", help="Skip web retrieval"),
) -> None:
    """Annotate a speech transcript and export results."""
    if sum(x is not None for x in (text, file, url)) != 1:
        raise typer.BadParameter("Provide exactly one of --text, --file, or --url")

    annotator = SpeechAnnotator(
        mode=mode,
        require_sources=require_sources,
        enable_web_search=not no_web_search,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Ingesting transcript...", total=None)
        if text:
            doc = annotator.from_text(text, title=title)
        elif file:
            doc = annotator.from_file(file, title=title)
        else:
            doc = annotator.from_url(url)  # type: ignore[arg-type]

        progress.add_task("Retrieving evidence and generating annotations...", total=None)
        annotated = annotator.annotate(doc)

    suffix = out.suffix.lower()
    if suffix == ".html":
        annotated.to_html(out)
    elif suffix == ".json":
        annotated.to_json(out)
    else:
        annotated.to_markdown(out)

    console.print(
        f"[green]Done![/green] {len(annotated.annotations)} annotations → {out}",
    )
    review_count = sum(1 for a in annotated.annotations if a.needs_human_review)
    if review_count:
        console.print(f"[yellow]{review_count} annotation(s) flagged for human review[/yellow]")


@app.command()
def seed(
    pdf: Path = typer.Option(DEFAULT_MALCOLM_PDF, "--pdf", help="PDF to extract speeches from"),
    source_id: str = typer.Option("malcolmx", "--source-id", help="Source identifier"),
    backend: str = typer.Option("pymupdf", "--backend", help="pymupdf (fast) or docling"),
    ocr: str = typer.Option("auto", "--ocr", help="OCR mode for docling: auto|off|easyocr"),
    force: bool = typer.Option(False, "--force", help="Re-extract even if manifest exists"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Max speeches to extract"),
) -> None:
    """Extract one .txt file per speech/interview/debate from a collected-speeches PDF."""
    if not pdf.exists():
        raise typer.BadParameter(f"PDF not found: {pdf}")

    console.print(f"[bold]Seeding speeches from[/bold] {pdf}")
    report = seed_speeches_from_pdf(
        pdf,
        source_id=source_id,
        backend=backend,
        ocr_engine=ocr,
        force=force,
        limit=limit,
    )
    console.print(
        f"[green]Done![/green] {report.speeches_written}/{report.speeches_found} speeches → "
        f"{report.output_dir}"
    )


@app.command("annotate-batch")
def annotate_batch(
    source_id: str = typer.Option("malcolmx", "--source-id", help="Seeded source id"),
    mode: AnnotationDepth = typer.Option(AnnotationDepth.LIGHT, "--mode", "-m"),
    limit: int = typer.Option(3, "--limit", help="Number of speeches to annotate"),
    require_sources: bool = typer.Option(True, "--require-sources/--no-require-sources"),
    no_web_search: bool = typer.Option(False, "--no-web-search"),
    smallest_first: bool = typer.Option(
        True,
        "--smallest-first/--alphabetical",
        help="Process short speeches first (recommended)",
    ),
    force: bool = typer.Option(False, "--force", help="Re-annotate even if output exists"),
    slug: Optional[str] = typer.Option(
        None,
        "--slug",
        help="Annotate one speech by slug (e.g. harlem-freedom-rally-1960)",
    ),
) -> None:
    """Annotate seeded speech .txt files (web search + evidence scoring)."""
    speeches_dir = SPEECHES_DIR / source_id
    if not speeches_dir.exists():
        raise typer.BadParameter(f"No seeded speeches at {speeches_dir}. Run: speechlens seed")

    if slug:
        path = speeches_dir / f"{slug}.txt"
        if not path.exists():
            raise typer.BadParameter(f"Speech not found: {path}")
        files = [path]
    else:
        files = list(speeches_dir.glob("*.txt"))
        if smallest_first:
            files.sort(key=lambda p: p.stat().st_size)
        else:
            files.sort()
        files = files[:limit]

    if not files:
        raise typer.BadParameter(f"No .txt files in {speeches_dir}")

    out_dir = ANNOTATED_DIR / source_id
    out_dir.mkdir(parents=True, exist_ok=True)
    annotator = SpeechAnnotator(
        mode=mode,
        require_sources=require_sources,
        enable_web_search=not no_web_search,
    )

    if not no_web_search:
        console.print(
            "[yellow]Web search is ON — each span does search + 3 LLM calls. "
            "This is slow (~1–3 min/span). Use --no-web-search for a fast pass, "
            "or --slug harlem-freedom-rally-1960 for one short speech.[/yellow]"
        )

    summary = []
    for path in files:
        stem = path.stem
        json_out = out_dir / f"{stem}.json"
        if json_out.exists() and not force:
            console.print(f"[dim]Skipping {path.name} (already annotated, use --force)[/dim]")
            continue

        size_kb = path.stat().st_size // 1024
        console.print(f"\n[bold]Annotating[/bold] {path.name} ({size_kb} KB)")
        doc = annotator.from_file(path)
        console.print(f"  {len(doc.segments)} segment(s) to process")

        checkpoint = out_dir / f"{stem}.partial.json"

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("starting…", total=None)

            def on_progress(msg: str, _seg: int, _total: int) -> None:
                progress.update(task, description=msg)

            annotated = annotator.annotate(
                doc,
                on_progress=on_progress,
                checkpoint_path=checkpoint,
            )

        annotated.to_markdown(out_dir / f"{stem}.md")
        annotated.to_json(json_out)
        if checkpoint.exists():
            checkpoint.unlink()
        summary.append(
            {
                "file": path.name,
                "annotations": len(annotated.annotations),
                "review": sum(1 for a in annotated.annotations if a.needs_human_review),
            }
        )
        console.print(
            f"  [green]saved[/green] {len(annotated.annotations)} annotations → {json_out.name}"
        )

    (out_dir / "batch.summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    console.print(f"\n[green]Batch complete![/green] {len(summary)} speech(es) → {out_dir}")


if __name__ == "__main__":
    app()
