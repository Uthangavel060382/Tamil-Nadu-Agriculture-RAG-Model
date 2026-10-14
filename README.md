# Tamil Nadu Agriculture RAG Model

A project for searching Tamil Nadu agriculture schemes, subsidies, and policy documents. It retrieves relevant text from indexed webpages and PDFs using multilingual embeddings.

## Tech Stack

- **Frontend:** Streamlit
- **Backend:** FastAPI
- **Vector database:** ChromaDB
- **Embeddings:** Sentence Transformers through LangChain
- **Document extraction:** Beautiful Soup, Playwright, and PyMuPDF

## Setup

Run these commands from the project folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Internet access is needed to install packages, download the embedding model on first use, and crawl websites. No LLM API key is required.

## Add Documents

Crawl the sources configured in `ingestion/sources.py`:

```powershell
python -m ingestion.crawl_sources --max-pages 8 --max-pdfs 3
```

Or ingest your own text file or PDF, replacing the example paths:

```powershell
python -m ingestion.ingest --text-file "data/scheme.txt" --scheme-name "Example Scheme"
python -m ingestion.ingest --pdf "data/policy.pdf"
```

Documents are indexed in `backend/chroma_db/`. Crawl results and errors are saved in `data/crawl_report.json`.

## Run the App

Start the backend:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal, activate the virtual environment and start the frontend:

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run frontend/app.py
```

- **App:** http://localhost:8501
- **API documentation:** http://127.0.0.1:8000/docs
- **Database health:** http://127.0.0.1:8000/health

Enter a question such as "What subsidies are available for irrigation?" to see matching passages and available source links.

## Project Structure

```text
backend/       FastAPI API, embeddings, and vector storage
frontend/      Streamlit search interface
ingestion/     Crawling, PDF extraction, and text ingestion
data/          Downloaded documents and crawl report
tests/         Application and crawler tests
requirements.txt
```

## Run Tests

```powershell
python -m unittest discover -s tests -v
```

## Notes

- The current version retrieves passages; it does not generate answers with an LLM.
- Scanned PDFs need OCR before ingestion.
- If search returns no results, check `/health` and ingest documents if the database is empty.
- Check official source documents for current scheme details and eligibility.
