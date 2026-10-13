"""Storage settings shared by ingestion and search, independent of cwd."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Reuse the existing database. The root chroma_db is an empty file.
CHROMA_DB_PATH = PROJECT_ROOT / "backend" / "chroma_db"
COLLECTION_NAME = "tamilnadu_agriculture_schemes"
