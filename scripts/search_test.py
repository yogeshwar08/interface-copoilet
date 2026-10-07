from app.retrieval.search import search_documents


def main():
    query = "What are the diagnostic criteria?"

    results = search_documents(query, top_k=5)

    print("\n=== SEARCH RESULTS ===")

    for rank, result in enumerate(results, start=1):
        payload = result.payload

        print("\n----------------------------")
        print(f"Rank       : {rank}")
        print(f"Score      : {result.score:.4f}")
        print(f"Document   : {payload['filename']}")
        print(f"Page       : {payload['page_number']}")

        print("\nText:")
        print(payload["text"])


if __name__ == "__main__":
    main()