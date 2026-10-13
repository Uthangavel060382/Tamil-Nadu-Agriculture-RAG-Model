import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings

from backend import embeddings, main, rag, vector_store
from ingestion.ingest import ingest_pdf, ingest_text, main as ingest_main


class TestEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        words = text.lower()
        return [float(words.count(term)) for term in ("soil", "card", "water", "farmer")] + [1.0]


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path_patch = patch.object(vector_store, "CHROMA_DB_PATH", Path(self.temp.name) / "db")
        self.path_patch.start()
        vector_store.get_collection.cache_clear()
        vector_store.get_vector_store.cache_clear()
        self.model_patch = patch.object(embeddings, "get_embeddings", return_value=TestEmbeddings())
        self.model_mock = self.model_patch.start()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        vector_store.get_vector_store.cache_clear()
        vector_store.get_collection.cache_clear()
        self.model_patch.stop()
        self.path_patch.stop()
        self.temp.cleanup()

    def test_empty_search_does_not_load_model(self):
        response = self.client.post("/search", json={"query": "soil card"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])
        self.model_mock.assert_not_called()
        self.assertEqual(self.client.get("/health").json(), {"status": "empty", "chunks": 0})

    def test_invalid_search_inputs(self):
        for query, top_k in (("", 5), ("  ", 5), ("soil", 0), ("soil", 51), ("x" * 2001, 5)):
            with self.subTest(query=query[:20], top_k=top_k):
                response = self.client.post("/search", json={"query": query, "top_k": top_k})
                self.assertEqual(response.status_code, 422)

    def test_ingestion_is_searchable_and_repeatable(self):
        metadata = {
            "scheme_name": "Soil Health Card", "financial_year": "2025-2026",
            "source_url": "https://example.test/schemes.pdf", "department": "Agriculture",
            "page": 24, "language": "Tamil", "documents_required": ["Identity", "Land record"],
        }
        text = "Soil health card information for farmers."
        self.assertEqual(ingest_text(text, metadata=metadata), 1)
        self.assertEqual(ingest_text(text, metadata=metadata), 1)
        self.assertEqual(vector_store.get_collection().count(), 1)
        response = self.client.post("/search", json={"query": " soil card ", "top_k": 5})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()["results"][0]
        self.assertEqual(result["scheme_name"], "Soil Health Card")
        self.assertEqual(result["year"], "2025-2026")
        self.assertEqual(result["source_url"], metadata["source_url"])
        self.assertEqual(result["page"], 24)
        self.assertEqual(result["content"], text)
        self.assertIsInstance(result["score"], float)
        stored = vector_store.get_collection().get()["metadatas"][0]
        self.assertEqual(json.loads(stored["documents_required"]), ["Identity", "Land record"])
        self.assertEqual(self.client.get("/health").json()["chunks"], 1)

    def test_pdf_pages_receive_actual_page_numbers(self):
        import pymupdf

        pdf_path = Path(self.temp.name) / "source.pdf"
        with pymupdf.open() as document:
            document.new_page().insert_text((72, 72), "Soil card for farmers.")
            document.new_page().insert_text((72, 72), "Water support for farmers.")
            document.save(pdf_path)
        self.assertEqual(ingest_pdf(pdf_path, metadata={"scheme_name": "Test", "page": 99}), 2)
        metadatas = vector_store.get_collection().get()["metadatas"]
        self.assertEqual({value["page"] for value in metadatas}, {1, 2})
        self.assertTrue(all(value["document_type"] == "PDF" for value in metadatas))

    def test_cli_rejects_invalid_metadata_and_empty_text(self):
        text_path = Path(self.temp.name) / "text.txt"
        text_path.write_text(" ", encoding="utf-8")
        metadata_path = Path(self.temp.name) / "metadata.json"
        metadata_path.write_text("[]", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ingest_main(["--text-file", str(text_path), "--metadata", str(metadata_path)]), 1)
            self.assertEqual(ingest_main(["--text-file", str(text_path)]), 1)

    def test_backend_failure_returns_service_unavailable(self):
        with patch.object(main, "search_schemes", side_effect=RuntimeError("private failure detail")):
            with self.assertLogs("backend.main", level="ERROR"):
                response = self.client.post("/search", json={"query": "soil"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private failure detail", response.text)

    def test_database_settings_do_not_depend_on_current_directory(self):
        from backend.config import CHROMA_DB_PATH, COLLECTION_NAME, PROJECT_ROOT

        self.assertTrue(CHROMA_DB_PATH.is_absolute())
        self.assertEqual(CHROMA_DB_PATH, PROJECT_ROOT / "backend" / "chroma_db")
        self.assertEqual(COLLECTION_NAME, "tamilnadu_agriculture_schemes")


if __name__ == "__main__":
    unittest.main()
