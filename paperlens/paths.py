from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PAPERS_RAW_DIR = DATA_DIR / "raw" / "papers"
PAPERS_DIR = DATA_DIR / "processed" / "papers"
PAPER_BLOCKS_DIR = PAPERS_DIR / "blocks"
PAPER_PAGES_DIR = PAPERS_DIR / "pages"
PAPER_ANNOTATED_DIR = PAPERS_DIR / "annotated"
PAPER_FIGURES_DIR = PAPERS_DIR / "figures"
PAPERS_MANIFEST = PAPERS_DIR / "corpus.manifest.json"

for path in (
    PAPERS_RAW_DIR,
    PAPERS_DIR,
    PAPER_BLOCKS_DIR,
    PAPER_PAGES_DIR,
    PAPER_ANNOTATED_DIR,
    PAPER_FIGURES_DIR,
):
    path.mkdir(parents=True, exist_ok=True)
