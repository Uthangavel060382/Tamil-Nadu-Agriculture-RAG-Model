import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from .rag import search_schemes
from .vector_store import get_collection

logger = logging.getLogger(__name__)


app = FastAPI(
    title="Tamil Nadu Agriculture Scheme API"
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Search query must not be blank")
        return value


@app.get("/")
def home():
    return {
        "status": "running"
    }


@app.post("/search")
def search(request: SearchRequest):
    try:
        results = search_schemes(request.query, request.top_k)
    except Exception as exc:
        logger.exception("Scheme search failed")
        raise HTTPException(
            status_code=503,
            detail="Search is unavailable. Check backend logs, installed dependencies, "
                   "and the embedding model download.",
        ) from exc

    return {
        "query": request.query,
        "count": len(results),
        "results": results
    }


@app.get("/health")
def health():
    try:
        count = get_collection().count()
    except Exception as exc:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="Database is unavailable.") from exc
    return {"status": "ready" if count else "empty", "chunks": count}
