"""Crawl configured official sources, follow scheme links, and index PDFs."""
import argparse
import asyncio
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import unquote, urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup
import requests

from backend.config import PROJECT_ROOT
from .ingest import ingest_pdf, ingest_text
from .sources import SOURCES

KEYWORDS = ("scheme", "subsid", "seed", "policy", "budget", "mission", "welfare", "திட்ட", "மானிய")
DOWNLOAD_DIR = PROJECT_ROOT / "data" / "downloads"
REPORT_PATH = PROJECT_ROOT / "data" / "crawl_report.json"


def normalize_url(url, base=""):
    absolute = urldefrag(urljoin(base, url.strip()))[0]
    parts = urlsplit(absolute)
    return absolute if parts.scheme in ("http", "https") and parts.hostname else None


def hostname(url):
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def relevant(label, url):
    value = unquote(f"{label} {urlsplit(url).path.rsplit('/', 1)[-1]}").lower()
    return any(keyword in value for keyword in KEYWORDS)


def parse_html(content, url):
    soup = BeautifulSoup(content, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else url
    links = []
    for anchor in soup.find_all("a", href=True):
        href = normalize_url(anchor["href"], url)
        if href:
            links.append({"text": anchor.get_text(" ", strip=True), "href": href})
    for element in soup(["script", "style", "nav", "footer", "form", "noscript"]):
        element.decompose()
    text = (soup.body or soup).get_text("\n", strip=True)
    return {"url": url, "title": title, "text": text, "links": links}


def fetch(session, url, timeout, retries, max_bytes=50 * 1024 * 1024):
    for attempt in range(retries + 1):
        try:
            with session.get(url, timeout=(timeout, timeout), stream=True) as response:
                if response.status_code in (408, 429, 500, 502, 503, 504) and attempt < retries:
                    time.sleep(min(2 ** attempt, 5))
                    continue
                response.raise_for_status()
                content = bytearray()
                for chunk in response.iter_content(65536):
                    content.extend(chunk)
                    if len(content) > max_bytes:
                        raise ValueError("Document exceeds the 50 MB download limit")
                return bytes(content), response.url, response.headers.get("Content-Type", "")
        except (requests.ConnectionError, requests.Timeout):
            if attempt >= retries:
                raise
            time.sleep(min(2 ** attempt, 5))
    raise RuntimeError("Download failed")


def crawl(sources, *, max_pages=8, max_pdfs=3, timeout=15, retries=1, render=False):
    if max_pages < 1 or max_pdfs < 1 or timeout < 1 or retries < 0:
        raise ValueError("Page/PDF limits and timeout must be positive; retries nonnegative")
    allowed = {hostname(source["url"]) for source in sources}
    # PDFs published by the TN government are often linked from the university portal.
    allowed.add("cms.tn.gov.in")
    queue = deque((source["url"], source["name"], dict(source)) for source in sources)
    visited = set()
    report = {"pages": 0, "pdfs": 0, "stored_chunks": 0, "documents": [], "errors": []}
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with requests.Session() as session:
        session.headers["User-Agent"] = "TamilNaduAgricultureSchemeCrawler/1.0"
        while queue:
            url, label, details = queue.popleft()
            url = normalize_url(url)
            if not url or url in visited or hostname(url) not in allowed:
                continue
            visited.add(url)
            is_pdf = urlsplit(url).path.lower().endswith(".pdf") or details.get("type") == "pdf"
            if is_pdf and report["pdfs"] >= max_pdfs:
                continue
            if not is_pdf and report["pages"] >= max_pages:
                continue
            # Limits count attempted downloads, including failures.
            counter = "pdfs" if is_pdf else "pages"
            report[counter] += 1
            print(f"Fetching: {url}", flush=True)
            try:
                content, final_url, content_type = fetch(session, url, timeout, retries)
                if hostname(final_url) not in allowed:
                    raise ValueError("Redirect left the configured official source domains")
                pdf_content = content.lstrip().startswith(b"%PDF-")
                if is_pdf and not pdf_content:
                    raise ValueError("Expected a PDF, but server returned other content")
                metadata = {
                    "source_url": final_url,
                    "state": "Tamil Nadu", "document_title": label,
                }
                if details.get("financial_year"):
                    metadata["financial_year"] = details["financial_year"]
                else:
                    year = re.search(r"(20\d{2})[-_](\d{2}|20\d{2})(?!\d)", final_url)
                    if year:
                        end_year = year[2] if len(year[2]) == 4 else year[1][:2] + year[2]
                        if int(end_year) == int(year[1]) + 1:
                            metadata["financial_year"] = f"{year[1]}-{end_year}"
                if pdf_content:
                    if not is_pdf:
                        if report["pdfs"] >= max_pdfs:
                            continue
                        report["pdfs"] += 1
                    pdf_path = DOWNLOAD_DIR / (hashlib.sha256(final_url.encode()).hexdigest()[:20] + ".pdf")
                    pdf_path.write_bytes(content)
                    metadata.update(pdf_url=final_url, document_type="PDF", scheme_name=label)
                    stored = ingest_pdf(pdf_path, metadata=metadata)
                    local_path = str(pdf_path)
                else:
                    if "html" not in content_type.lower() and not content.lstrip().startswith(b"<"):
                        raise ValueError(f"Unsupported document type: {content_type}")
                    page = parse_html(content, final_url)
                    if render or len(page["text"]) < 100:
                        from .crawler import scrape_page
                        page = asyncio.run(scrape_page(final_url, timeout=timeout, retries=retries))
                    metadata.update(document_type="Website", document_title=page["title"], scheme_name=page["title"])
                    stored = ingest_text(page["text"], metadata=metadata)
                    local_path = str(DOWNLOAD_DIR / (hashlib.sha256(final_url.encode()).hexdigest()[:20] + ".html"))
                    Path(local_path).write_bytes(content)
                    candidates = [
                        link for link in page["links"]
                        if hostname(link["href"]) in allowed and relevant(link["text"], link["href"])
                    ]
                    # Prefer recent policy documents to historical material.
                    candidates.sort(key=lambda link: (
                        "2026" not in link["href"], "2025" not in link["href"],
                        not link["href"].lower().endswith(".pdf")
                    ))
                    queue.extend((link["href"], link["text"] or page["title"], {}) for link in candidates)
                if not stored:
                    raise ValueError("No extractable text; image-only PDFs need OCR")
                report["stored_chunks"] += stored
                report["documents"].append({"url": final_url, "chunks": stored, "local_path": local_path})
                print(f"Stored {stored} chunks: {label}", flush=True)
            except Exception as exc:
                report["errors"].append({"url": url, "error": str(exc)[:1000]})
                print(f"Skipped {url}: {str(exc)[:300]}", flush=True)
            time.sleep(1)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-pages", type=int, default=8)
    parser.add_argument("--max-pdfs", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--render", action="store_true", help="Use Playwright for rendered webpages")
    parser.add_argument("--offline-model", action="store_true", help="Use only the cached embedding model")
    parser.add_argument("--url", action="append", help="Override configured seeds; may be repeated")
    args = parser.parse_args(argv)
    if args.offline_model:
        os.environ["HF_HUB_OFFLINE"] = "1"
    sources = [{"name": url, "url": url, "type": "website"} for url in args.url] if args.url else SOURCES
    try:
        report = crawl(sources, max_pages=args.max_pages, max_pdfs=args.max_pdfs,
                       timeout=args.timeout, retries=args.retries, render=args.render)
    except Exception as exc:
        print(f"Crawl failed: {exc}")
        return 1
    print(f"Stored {report['stored_chunks']} chunks from {len(report['documents'])} documents. "
          f"Failed URLs: {len(report['errors'])}. Report: {REPORT_PATH}")
    return 0 if report["stored_chunks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
