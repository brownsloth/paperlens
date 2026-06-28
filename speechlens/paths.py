from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SPEECHES_DIR = PROCESSED_DIR / "speeches"
ANNOTATED_DIR = PROCESSED_DIR / "annotated"
DEFAULT_MALCOLM_PDF = RAW_DIR / "MalcolmX.pdf"

for path in (RAW_DIR, PROCESSED_DIR, SPEECHES_DIR, ANNOTATED_DIR):
    path.mkdir(parents=True, exist_ok=True)
