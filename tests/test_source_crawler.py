import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests

from ingestion import crawl_sources as crawler


class SourceCrawlerTests(unittest.TestCase):
    def test_link_resolution_and_text_extraction(self):
        page = crawler.parse_html(
            b'<html><title>Seeds</title><body><script>ignore</script>'
            b'<p>Certified seeds for farmers</p><a href="../schemes.pdf#page=2">Seed schemes</a>'
            b'<a href="mailto:test@example.com">Email</a></body></html>',
            "https://example.test/info/index.html",
        )
        self.assertEqual(page["title"], "Seeds")
        self.assertNotIn("ignore", page["text"])
        self.assertEqual(page["links"][0]["href"], "https://example.test/schemes.pdf")
        self.assertEqual(len(page["links"]), 1)

    def test_follow_pdf_deduplicate_and_report_failures(self):
        html = (b'<html><title>Scheme portal</title><body>' + b'Seed information ' * 10 +
                b'<a href="/seeds.pdf">Seed scheme</a><a href="/seeds.pdf#page=3">Same PDF</a>'
                b'<a href="https://unrelated.test/scheme.pdf">External scheme</a>'
                b'<a href="/missing-policy">Policy</a></body></html>')
        def download(session, url, timeout, retries):
            if url.endswith("/seeds.pdf"):
                return b"%PDF-test", url, "application/pdf"
            if url.endswith("/missing-policy"):
                raise requests.Timeout("Source unavailable")
            return html, url, "text/html"
        with tempfile.TemporaryDirectory() as folder:
            report_path = Path(folder) / "report.json"
            with patch.object(crawler, "DOWNLOAD_DIR", Path(folder) / "downloads"), \
                 patch.object(crawler, "REPORT_PATH", report_path), \
                 patch.object(crawler, "fetch", side_effect=download) as fetched, \
                 patch.object(crawler, "ingest_text", return_value=2), \
                 patch.object(crawler, "ingest_pdf", return_value=3) as pdf_ingest, \
                 patch.object(crawler.time, "sleep"):
                report = crawler.crawl([{"name": "Portal", "url": "https://example.test", "type": "website"}])
            self.assertEqual(report["stored_chunks"], 5)
            self.assertEqual(len(report["documents"]), 2)
            self.assertEqual(len(report["errors"]), 1)
            self.assertEqual(fetched.call_count, 3)
            pdf_ingest.assert_called_once()
            self.assertEqual(pdf_ingest.call_args.kwargs["metadata"]["source_url"], "https://example.test/seeds.pdf")
            self.assertEqual(json.loads(report_path.read_text())["stored_chunks"], 5)
            self.assertTrue(list((Path(folder) / "downloads").glob("*.pdf")))

    def test_limits_count_failed_downloads(self):
        sources = [{"name": str(i), "url": f"https://example.test/{i}", "type": "website"} for i in range(5)]
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(crawler, "DOWNLOAD_DIR", Path(folder)), \
                 patch.object(crawler, "REPORT_PATH", Path(folder) / "report.json"), \
                 patch.object(crawler, "fetch", side_effect=requests.Timeout("Unavailable")) as fetched, \
                 patch.object(crawler.time, "sleep"):
                report = crawler.crawl(sources, max_pages=2)
            self.assertEqual(fetched.call_count, 2)
            self.assertEqual(report["pages"], 2)
            self.assertEqual(report["stored_chunks"], 0)


if __name__ == "__main__":
    unittest.main()
