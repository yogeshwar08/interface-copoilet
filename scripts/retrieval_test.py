from app.retrieval.search import retrieve_context


def main():
    query = "What are the diagnostic criteria?"

    results = retrieve_context(
        query,
        candidate_k=10,
        top_k=5,
    )

    print("\n=== FINAL RETRIEVAL RESULTS ===")

    for rank, result in enumerate(results, start=1):
        payload = result["payload"]

        print("\n----------------------------")
        print(f"Rank       : {rank}")
        print(f"Rerank     : {result['score']:.4f}")
        print(f"Document   : {payload['filename']}")
        print(f"Page       : {payload['page_number']}")
        print(f"Chunk ID    : {payload['chunk_id']}")

        print("\nText:")
        print(payload["text"])


if __name__ == "__main__":
    main()