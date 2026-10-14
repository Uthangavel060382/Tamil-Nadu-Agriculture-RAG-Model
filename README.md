# Tamil Nadu Agriculture RAG Model

Search Tamil Nadu agriculture schemes, subsidies, and policy documents using semantic similarity. The project collects webpage and PDF text, indexes it in a persistent Chroma database, and exposes relevant passages through a FastAPI backend and a Streamlit interface.

The current implementation provides the retrieval stage of a Retrieval-Augmented Generation (RAG) system. It returns source passages and metadata; it does not call an LLM or generate conversational answers.

## Features

- Search with multilingual embeddings, including Tamil and English queries.
- Ingest local text files, text-based PDFs, or individual webpages.
- Crawl configured sources and follow relevant scheme and policy links within allowed domains.
- Retain source URLs, PDF page numbers, document types, and supplied scheme metadata.
- Reuse a persistent vector database across ingestion and search.
- Upsert identical text and metadata using deterministic chunk IDs.
- Inspect API status and indexed chunk counts through health endpoints.

## How it works

```text
Official webpages / PDFs / local text
                 |
        Extract and clean text
                 |
    Split into overlapping chunks
                 |
    Create multilingual embeddings
                 |
       Persistent Chroma database
                 |
Query -> FastAPI similarity search -> Streamlit results + source links
```

The embedding model is `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, running on CPU with normalized embeddings. Text is split into chunks of 800 characters with 150 characters of overlap.

## Technology stack

| Component | Technology |
| --- | --- |
| Search API | FastAPI, Uvicorn, Pydantic |
| User interface | Streamlit, Requests |
| Embeddings | Sentence Transformers, LangChain Hugging Face |
| Vector storage | ChromaDB, LangChain Chroma |
| Web extraction | Requests, Beautiful Soup, Playwright |
| PDF extraction | PyMuPDF |
| Text splitting | LangChain text splitters |
| Tests | Python `unittest`, FastAPI TestClient, mocks |

## Project structure

```text
Tamil-Nadu-Agriculture-RAG-Model/
|-- backend/
|   |-- config.py          # Shared database path and collection name
|   |-- embeddings.py      # Cached multilingual embedding model
|   |-- main.py            # FastAPI endpoints and input validation
|   |-- rag.py             # Similarity search and response formatting
|   |-- vector_store.py    # Chroma collection and LangChain integration
|   `-- chroma_db/         # Runtime vector database (ignored by Git)
|-- frontend/
|   `-- app.py             # Streamlit search interface
|-- ingestion/
|   |-- sources.py         # Configured source URLs
|   |-- crawl_sources.py   # Bounded source crawler and ingestion
|   |-- crawler.py         # Playwright webpage extraction
|   |-- pdf_loader.py      # PDF download and page text extraction
|   |-- cleaner.py         # Text cleanup
|   |-- chunker.py         # Overlapping text chunks
|   `-- ingest.py          # Text, PDF, and webpage ingestion CLI
|-- data/
|   |-- downloads/         # Files saved by the source crawler
|   `-- crawl_report.json  # Latest crawl summary and errors
|-- tests/                 # Application and crawler tests
|-- app.py                 # Command-line crawler smoke check
|-- requirements.txt
`-- README.md
```

## Installation

Use a Python environment compatible with the packages in `requirements.txt`; Python 3.11 or 3.12 is a reasonable starting point. Internet access is needed to install dependencies, download the embedding model on first use, and crawl remote sources.

From the project root, run the following in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

On macOS or Linux, activate the environment with `source .venv/bin/activate` instead.

Chromium is required for individual webpage ingestion, the crawler smoke check, and browser-rendered crawling. Local text and PDF ingestion do not require a browser. The backend does not require an LLM API key or a populated `.env` file.

## Add documents to the search index

Run these commands from the project root with the virtual environment active.

### Crawl configured sources

```powershell
python -m ingestion.crawl_sources --max-pages 8 --max-pdfs 3 --timeout 15 --retries 1
```

Seeds in `ingestion/sources.py` include TNAU Agritech, Tamil Nadu agriculture budget and policy documents, Agrisnet, Horticulture, and Agricultural Marketing portals. These are configured URLs, and their availability may change.

The crawler saves downloaded files to `data/downloads/` and writes a summary, document list, and failures to `data/crawl_report.json`. Page and PDF limits count attempted downloads, including failures. Review the report even when the command succeeds: it exits successfully when at least one chunk is stored, so some sources may still have failed.

Optional flags:

| Flag | Purpose |
| --- | --- |
| `--render` | Use Playwright to render webpages; short extracted pages also trigger browser rendering automatically. |
| `--offline-model` | Use only a previously cached embedding model. Source downloads still require network access. |
| `--url URL` | Override the configured seeds; repeat the flag to supply multiple URLs. |

### Ingest a local text file

Replace the sample paths and labels below with your own files and document details.

```powershell
python -m ingestion.ingest --text-file "data/scheme.txt" --scheme-name "Example Scheme"
```

### Ingest a local PDF

```powershell
python -m ingestion.ingest --pdf "data/policy.pdf" --metadata "data/metadata.json"
```

Example `data/metadata.json`:

```json
{
  "scheme_name": "Example Agriculture Scheme",
  "department": "Agriculture",
  "financial_year": "2025-2026",
  "source_url": "https://example.com/replace-with-official-document.pdf",
  "language": "English"
}
```

The metadata is supplied by you, rather than automatically verified. PDF ingestion records actual, one-based page numbers. Scanned or image-only PDFs require OCR before ingestion; OCR is not included.

### Ingest one webpage

```powershell
python -m ingestion.ingest --url "https://agritech.tnau.ac.in/"
```

The ingestion CLI accepts exactly one of `--text-file`, `--pdf`, or `--url`. Add `--metadata`, `--source-url`, or `--scheme-name` as needed. Repeating identical text and metadata reuses existing chunk IDs; changed content or metadata creates new IDs and does not remove older chunks automatically.

## Run the application

Start the backend from the project root:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal, activate the same virtual environment and start the interface:

```powershell
python -m streamlit run frontend/app.py
```

Open the UI at <http://localhost:8501> and the API documentation at <http://127.0.0.1:8000/docs>. The frontend currently calls `http://127.0.0.1:8000/search` directly, so keep the backend on that address unless you update `frontend/app.py`.

Example questions:

- What support is available for certified seeds?
- Are there subsidies for irrigation equipment?
- What schemes support horticulture farmers?

Results contain retrieved passages, available scheme details, source links, and distance scores. Lower distance scores indicate closer matches; scores are not confidence percentages. A result represents a text chunk, so multiple results may come from the same document.

The root `app.py` is a crawler smoke check, not the UI entry point. Run it separately when checking browser extraction:

```powershell
python app.py --url "https://agritech.tnau.ac.in/" --timeout 60 --retries 1
```

## API reference

| Method | Endpoint | Behavior |
| --- | --- | --- |
| `GET` | `/` | Returns `{"status": "running"}`. |
| `GET` | `/health` | Returns `status` (`ready` or `empty`) and indexed `chunks`; returns HTTP 503 when the database is unavailable. |
| `POST` | `/search` | Retrieves matching chunks for a query. |

Example search in PowerShell:

```powershell
$searchBody = @{ query = "seed subsidy for farmers"; top_k = 5 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/search" -Method Post -ContentType "application/json" -Body $searchBody
```

The response includes `query`, `count`, and a `results` array. Each result contains `scheme_name`, `department`, `year`, `content`, `source_url`, `page`, `document_type`, and `score`. Missing metadata may produce empty fields, a null page, or `Unknown Scheme`.

Queries must be nonblank and at most 2,000 characters. `top_k` defaults to 5 and must be between 1 and 50. Invalid requests return HTTP 422; search failures return HTTP 503. An empty collection returns an empty results array without loading the embedding model.

## Configuration and storage

| Setting | Location / default |
| --- | --- |
| Database directory | `backend/config.py`: `backend/chroma_db/`, resolved from the project root |
| Collection name | `backend/config.py`: `tamilnadu_agriculture_schemes` |
| Embedding model and device | `backend/embeddings.py`: multilingual MiniLM, CPU |
| Chunk size / overlap | `ingestion/chunker.py`: 800 / 150 characters |
| Crawl seed URLs | `ingestion/sources.py` |
| Frontend API address | `frontend/app.py`: `http://127.0.0.1:8000/search` |

The root-level `chroma_db` file is not the active database. Keep ingestion and search on the same model and collection. If you change the embedding model or chunking strategy, build a separate index or deliberately rebuild the existing one to avoid mixing incompatible data.

## Tests

Run the automated suite from the project root:

```powershell
python -m unittest discover -s tests -v
```

The suite covers API validation, empty-index behavior, ingestion and retrieval, repeat ingestion, PDF page metadata, database paths, crawler retries, link filtering, crawl limits, and failure reports. Tests use temporary storage and mocked embedding/network behavior, so they do not verify live portal availability or real-model retrieval quality.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| UI cannot connect to FastAPI | Start the backend on `127.0.0.1:8000` and check `/docs`. |
| No search results | Inspect `/health`; ingest documents if `chunks` is zero. |
| First search or ingestion is slow | The embedding model may be downloading or initializing on CPU. |
| Model download fails | Check network access and model-cache availability. Use `--offline-model` for crawling only after the model has been cached. |
| Playwright browser is missing | Run `python -m playwright install chromium` in the active environment. |
| A source times out or fails | Review `data/crawl_report.json`; adjust timeout/retries or update the configured URL. |
| PDF has no extractable text | Apply OCR externally before ingestion. |
| Python cannot import `backend` or `ingestion` | Run the documented module commands from the project root. |

## Current limitations

- Retrieval does not generate answers, determine eligibility, or submit applications.
- Crawling is bounded and does not guarantee complete or current coverage of every scheme.
- Source pages and document titles may be used as scheme names; structured eligibility and benefit extraction is not implemented.
- Multilingual embeddings support semantic queries, but retrieval quality depends on the indexed documents and should be evaluated on representative questions.
- The API has no authentication or rate limiting; the documented launch command binds it locally for development.

Check the linked official documents for current eligibility, benefits, deadlines, and application procedures before acting on a retrieved passage.

