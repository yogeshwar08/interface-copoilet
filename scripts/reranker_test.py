from app.retrieval.search import hybrid_search
from app.retrieval.reranker import reranker


def main():
    query = "What are the diagnostic criteria?"

    candidates = hybrid_search(
        query,
        top_k=10,
        candidate_k=10,
    )

    results = reranker.rerank(
        query,
        candidates,
        top_k=5,
    )

    print("\n=== RERANKED RESULTS ===")

    for rank, result in enumerate(results, start=1):
        payload = result["payload"]

        print("\n----------------------------")
        print(f"Rank       : {rank}")
        print(f"Score      : {result['score']:.4f}")
        print(f"Document   : {payload['filename']}")
        print(f"Page       : {payload['page_number']}")
        print(f"Chunk ID    : {payload['chunk_id']}")

        print("\nText:")
        print(payload["text"])


if __name__ == "__main__":
    main()