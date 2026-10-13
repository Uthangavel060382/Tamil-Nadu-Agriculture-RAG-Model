"""Manual crawler smoke check; accepts the same options as the root app.py."""
# Support both python -m ingestion.test_crawler and execution from ingestion/.
if __package__:
    from app import main
else:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app import main


if __name__ == "__main__":
    raise SystemExit(main())
