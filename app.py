"""Command-line crawler smoke check. The Streamlit UI is frontend/app.py."""
import argparse
import asyncio

from ingestion.crawler import scrape_page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://agritech.tnau.ac.in/")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=1)
    args = parser.parse_args()
    try:
        result = asyncio.run(scrape_page(args.url, timeout=args.timeout, retries=args.retries))
        print(result["title"])
        print(result["text"][:2000])
        return 0
    except Exception as exc:
        print(f"Crawler failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
