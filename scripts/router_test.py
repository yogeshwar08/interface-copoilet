import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.graph import agent_graph


def test_query(query: str):
    result = agent_graph.invoke(
        {
            "query": query,
            "route": "",
            "context": "",
            "sources": [],
            "response": "",
        }
    )

    print("\n----------------------------")
    print(f"Query    : {query}")
    print(f"Route    : {result['route']}")

    print("\nSources:")

    for source in result["sources"]:
        source_id = source.get("source_number", source.get("id", source.get("chunk_id", "?")))
        print(
            f"[{source_id}] "
            f"{source.get('filename', 'doc')} "
            f"- Page {source.get('page', '?')}"
        )

    print("\nResponse:")
    print(result["response"])


def main():
    test_query(
        "What are the diagnostic criteria in the guideline?"
    )

    test_query(
        "How many records are in the database?"
    )

    test_query(
        "What is the current weather?"
    )


if __name__ == "__main__":
    main()