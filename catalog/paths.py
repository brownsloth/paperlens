from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CATEGORIES_PATH = PROCESSED_DIR / "categories.json"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
