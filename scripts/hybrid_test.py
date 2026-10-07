import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval.search import hybrid_search


def main():
    query = "What are the diagnostic criteria?"

    results = hybrid_search(
        query,
        top_k=5,
    )

    print("\n=== HYBRID SEARCH RESULTS ===")

    for rank, result in enumerate(results, start=1):
        payload = result["payload"]

        print("\n----------------------------")
        print(f"Rank       : {rank}")
        print(f"RRF Score  : {result['score']:.6f}")
        print(f"Document   : {payload['filename']}")
        print(f"Page       : {payload['page_number']}")
        print(f"Chunk ID    : {payload['chunk_id']}")

        print("\nText:")
        print(payload["text"])


if __name__ == "__main__":
    main()