from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from paperlens.annotate import PaperAnnotator, load_parsed, parse_paper
from paperlens.arxiv import fetch_real_world_learning_papers, fetch_starter_papers, load_manifest
from catalog.store import ensure_real_world_learning_category
from paperlens.library import list_papers
from paperlens.models import AnnotationLens

app = typer.Typer(help="PaperLens: source-grounded annotation on research PDFs")
console = Console()


@app.command("fetch-starter")
def fetch_starter(
    limit: Optional[int] = typer.Option(None, "--limit", help="Max papers to fetch"),
    force: bool = typer.Option(False, "--force", help="Re-download PDFs"),
) -> None:
    """Download starter Schmidhuber papers from arXiv (polite rate limits)."""
    console.print("[cyan]Fetching starter papers from arXiv…[/cyan]")
    entries = fetch_starter_papers(limit=limit, force=force)
    ok = sum(1 for e in entries if e.get("pdf_status") == "available")
    console.print(f"[green]Done.[/green] {ok}/{len(entries)} PDFs available → data/processed/papers/corpus.manifest.json")


@app.command("fetch-real-world-learning")
def fetch_real_world_learning(
    force: bool = typer.Option(False, "--force", help="Re-download PDFs"),
    parse_all: bool = typer.Option(True, "--parse/--no-parse", help="Parse downloaded PDFs"),
) -> None:
    """Download Real World Learning corpus and seed category."""
    console.print("[cyan]Fetching Real World Learning papers…[/cyan]")
    entries = fetch_real_world_learning_papers(force=force)
    ok = sum(1 for e in entries if e.get("pdf_status") == "available")
    meta = sum(1 for e in entries if e.get("pdf_status") == "metadata_only")
    failed = len(entries) - ok - meta
    console.print(
        f"[green]Downloaded[/green] {ok} PDFs, {meta} metadata-only, {failed} failed "
        f"→ data/processed/papers/corpus.manifest.json"
    )
    cat = ensure_real_world_learning_category()
    console.print(f"[green]Category[/green] {cat['category_id']}: {cat['total']} papers linked")

    if parse_all:
        for entry in entries:
            if entry.get("pdf_status") != "available":
                continue
            pid = entry["paper_id"]
            if not force and load_parsed(pid):
                continue
            try:
                doc = parse_paper(
                    Path(entry["pdf_path"]),
                    paper_id=pid,
                    title=entry.get("title", pid),
                    authors=entry.get("authors"),
                    year=entry.get("year"),
                    arxiv_id=entry.get("arxiv_id"),
                    abstract=entry.get("abstract"),
                )
                console.print(f"  [dim]parsed[/dim] {pid}: {doc.paper.page_count} pages")
            except Exception as exc:
                console.print(f"  [red]parse failed[/red] {pid}: {exc}")


@app.command("parse")
def parse_cmd(
    paper_id: str = typer.Argument(..., help="Paper ID from manifest"),
    force: bool = typer.Option(False, "--force", help="Re-parse and re-render pages"),
) -> None:
    """Extract layout blocks + render page images for one paper."""
    entry = _manifest_entry(paper_id)
    pdf_path = Path(entry["pdf_path"])
    if not pdf_path.exists():
        raise typer.BadParameter(f"PDF not found: {pdf_path}. Run fetch-starter first.")

    if not force and load_parsed(paper_id):
        doc = load_parsed(paper_id)
        assert doc
        console.print(f"[yellow]Already parsed[/yellow] {doc.paper.block_count} blocks, {doc.paper.page_count} pages")
        return

    doc = parse_paper(
        pdf_path,
        paper_id=paper_id,
        title=entry.get("title", paper_id),
        authors=entry.get("authors"),
        year=entry.get("year"),
        arxiv_id=entry.get("arxiv_id"),
        abstract=entry.get("abstract"),
        force=force,
    )
    console.print(
        f"[green]Parsed[/green] {doc.paper.title}: {doc.paper.block_count} blocks, {doc.paper.page_count} pages"
    )


@app.command("annotate")
def annotate_cmd(
    paper_id: str = typer.Argument(..., help="Paper ID"),
    lens: AnnotationLens = typer.Option(AnnotationLens.BEGINNER, "--lens", "-l"),
    max_candidates: int = typer.Option(12, "--max-candidates"),
) -> None:
    """Generate block-anchored annotations for a parsed paper."""
    doc = load_parsed(paper_id)
    if not doc:
        raise typer.BadParameter(f"Paper not parsed: {paper_id}. Run: paperlens parse {paper_id}")

    annotator = PaperAnnotator(lens=lens, max_candidates=max_candidates)
    result = annotator.annotate(doc)
    console.print(f"[green]Annotated[/green] {len(result.annotations)} spans ({lens.value} lens)")


@app.command("list")
def list_cmd() -> None:
    """List papers in the corpus."""
    papers = list_papers()
    if not papers:
        console.print("No papers yet. Run: paperlens fetch-starter")
        raise typer.Exit(0)

    table = Table("ID", "Title", "Pages", "Blocks", "PDF", "Annotated")
    for p in papers:
        table.add_row(
            p.paper_id,
            (p.title[:50] + "…") if len(p.title) > 50 else p.title,
            str(p.page_count or "—"),
            str(p.block_count or "—"),
            p.pdf_status,
            "yes" if p.has_annotations else "no",
        )
    console.print(table)


def _manifest_entry(paper_id: str) -> dict:
    manifest = load_manifest()
    for entry in manifest.get("papers", []):
        if entry["paper_id"] == paper_id:
            if entry.get("pdf_status") != "available":
                raise typer.BadParameter(f"PDF unavailable for {paper_id}: {entry.get('pdf_status')}")
            return entry
    raise typer.BadParameter(f"Unknown paper_id: {paper_id}")


if __name__ == "__main__":
    app()
