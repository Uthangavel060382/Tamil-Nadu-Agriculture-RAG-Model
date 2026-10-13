"""Ingest source text or PDF pages into the collection searched by the API."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from backend.vector_store import get_vector_store
from .cleaner import clean_text


def ingest_text(text, source_url="", scheme_name="", *, metadata=None):
    from .chunker import create_chunks

    chunks = create_chunks(clean_text(text))
    if not chunks:
        return 0
    values = dict(metadata or {})
    if source_url:
        values["source_url"] = source_url
    if scheme_name:
        values["scheme_name"] = scheme_name
    values.setdefault("source_url", "")
    if not values.get("scheme_name"):
        values["scheme_name"] = "Unknown Scheme"
    # Chroma metadata values must be scalars. Preserve lists as JSON strings.
    values = {
        key: value if isinstance(value, (str, int, float, bool)) else json.dumps(value, ensure_ascii=False)
        for key, value in values.items() if value is not None
    }
    metadatas = [dict(values, chunk=index) for index in range(len(chunks))]
    # Repeat ingestion of the same text/metadata upserts the same IDs.
    ids = [hashlib.sha256(json.dumps(
        [chunk, details], ensure_ascii=False, sort_keys=True
    ).encode("utf-8")).hexdigest() for chunk, details in zip(chunks, metadatas)]
    get_vector_store().add_texts(texts=chunks, metadatas=metadatas, ids=ids)
    return len(chunks)


def ingest_pdf(pdf_path, *, metadata=None):
    from .pdf_loader import extract_pdf_text

    total = 0
    for page in extract_pdf_text(pdf_path):
        details = dict(metadata or {}, document_type="PDF", page=page["page"])
        total += ingest_text(page["text"], metadata=details)
    return total


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text-file", type=Path)
    source.add_argument("--pdf", type=Path, help="Local PDF path")
    source.add_argument("--url", help="Webpage URL to crawl")
    parser.add_argument("--metadata", type=Path, help="JSON object containing scheme/source metadata")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--scheme-name", default="")
    args = parser.parse_args(argv)
    try:
        metadata = json.loads(args.metadata.read_text(encoding="utf-8-sig")) if args.metadata else {}
        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a JSON object")
        if args.source_url:
            metadata["source_url"] = args.source_url
        if args.scheme_name:
            metadata["scheme_name"] = args.scheme_name
        if args.pdf:
            stored = ingest_pdf(args.pdf, metadata=metadata)
        elif args.text_file:
            metadata.setdefault("document_type", "Text")
            stored = ingest_text(args.text_file.read_text(encoding="utf-8-sig"), metadata=metadata)
        else:
            from .crawler import scrape_page

            result = asyncio.run(scrape_page(args.url))
            metadata.setdefault("source_url", result["url"])
            metadata.setdefault("scheme_name", result["title"])
            metadata.setdefault("document_type", "Website")
            stored = ingest_text(result["text"], metadata=metadata)
        if not stored:
            raise ValueError("No extractable text found. Scanned PDFs need OCR before ingestion.")
        print(f"Stored {stored} chunks in the scheme search database.")
        return 0
    except Exception as exc:
        print(f"Ingestion failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
