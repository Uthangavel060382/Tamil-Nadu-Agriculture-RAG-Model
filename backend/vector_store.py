from functools import lru_cache

from .config import CHROMA_DB_PATH, COLLECTION_NAME, PROJECT_ROOT


@lru_cache(maxsize=1)
def get_collection():
    """Access the collection without downloading an embedding model."""
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=None)


@lru_cache(maxsize=1)
def get_vector_store():
    from langchain_chroma import Chroma
    from .embeddings import get_embeddings

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DB_PATH),
    )
