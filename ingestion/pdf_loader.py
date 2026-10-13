#Read PDF files

import requests
import pymupdf
from pathlib import Path


def download_pdf(url, output_path):

    response = requests.get(
        url,
        timeout=60
    )

    response.raise_for_status()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_bytes(
        response.content
    )


def extract_pdf_text(pdf_path):

    pages = []
    with pymupdf.open(pdf_path) as document:
        for page_number, page in enumerate(document):
            pages.append({"page": page_number + 1, "text": page.get_text()})

    return pages
