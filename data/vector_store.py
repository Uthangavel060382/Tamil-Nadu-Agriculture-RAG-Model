"""Compatibility access to the same collection used by the backend."""
from backend.vector_store import get_collection, get_vector_store


def __getattr__(name):
    if name == "collection":
        return get_collection()
    raise AttributeError(name)
