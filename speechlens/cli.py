from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from speechlens.annotator import SpeechAnnotator
from speechlens.models import AnnotationDepth

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
) -> None:
    """Annotate a speech transcript and export results."""
    if sum(x is not None for x in (text, file, url)) != 1:
        raise typer.BadParameter("Provide exactly one of --text, --file, or --url")

    annotator = SpeechAnnotator(mode=mode, require_sources=require_sources)

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

        progress.add_task("Generating annotations...", total=None)
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


if __name__ == "__main__":
    app()
