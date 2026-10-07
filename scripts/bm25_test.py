from app.retrieval.bm25 import build_bm25_index, tokenize


def main():
    query = "What are the diagnostic criteria?"

    bm25, documents = build_bm25_index()

    query_tokens = tokenize(query)

    scores = bm25.get_scores(query_tokens)

    ranked = sorted(
        zip(scores, documents),
        key=lambda x: x[0],
        reverse=True,
    )

    print("\n=== BM25 SEARCH RESULTS ===")

    for rank, (score, document) in enumerate(ranked[:5], start=1):
        payload = document["payload"]

        print("\n----------------------------")
        print(f"Rank       : {rank}")
        print(f"Score      : {score:.4f}")
        print(f"Document   : {payload['filename']}")
        print(f"Page       : {payload['page_number']}")

        print("\nText:")
        print(payload["text"])


if __name__ == "__main__":
    main()