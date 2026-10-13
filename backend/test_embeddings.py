"""Manual embedding smoke check: python -m backend.test_embeddings."""
from backend.embeddings import get_embeddings


def main():
    embeddings = get_embeddings()
    for label, text in (
        ("English", "Subsidy support for drip irrigation farmers"),
        ("Tamil", "\u0b9a\u0bca\u0b9f\u0bcd\u0b9f\u0bc1 \u0ba8\u0bc0\u0bb0\u0bcd \u0baa\u0bbe\u0b9a\u0ba9 \u0bb5\u0bbf\u0bb5\u0b9a\u0bbe\u0baf\u0bbf\u0b95\u0bb3\u0bc1\u0b95\u0bcd\u0b95\u0bbe\u0ba9 \u0bae\u0bbe\u0ba9\u0bbf\u0baf\u0bae\u0bcd"),
    ):
        print(f"{label} embedding length:", len(embeddings.embed_query(text)))


if __name__ == "__main__":
    main()
