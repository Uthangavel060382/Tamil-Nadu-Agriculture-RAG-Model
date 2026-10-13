from .vector_store import get_collection, get_vector_store


def search_schemes(query: str, top_k: int = 5):
    query = query.strip()
    if not query:
        raise ValueError("Search query must not be blank")
    if not 1 <= top_k <= 50:
        raise ValueError("top_k must be between 1 and 50")
    count = get_collection().count()
    if not count:
        return []
    vector_store = get_vector_store()

    results = vector_store.similarity_search_with_score(
        query,
        k=min(top_k, count)
    )

    formatted_results = []

    for document, score in results:
        metadata = document.metadata or {}

        formatted_results.append(
            {
                "scheme_name": metadata.get(
                    "scheme_name",
                    "Unknown Scheme"
                ),
                "department": metadata.get(
                    "department",
                    ""
                ),
                "year": metadata.get(
                    "financial_year",
                    metadata.get("year", "")
                ),
                "content": document.page_content,
                "source_url": metadata.get(
                    "source_url",
                    ""
                ),
                "page": metadata.get(
                    "page",
                    None
                ),
                "document_type": metadata.get(
                    "document_type",
                    ""
                ),
                "score": float(score)
            }
        )

    return formatted_results
