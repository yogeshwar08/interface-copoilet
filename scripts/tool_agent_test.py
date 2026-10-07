from app.agents.graph import agent_graph


def run_query(query: str):

    print("\n" + "=" * 60)
    print(f"QUERY: {query}")
    print("=" * 60)

    initial_state = {
        "query": query,
        "route": "",
        "context": "",
        "sources": [],
        "response": "",
        "sql": "",
        "sql_rows": [],
    }

    result = agent_graph.invoke(
        initial_state
    )

    print("\nRoute:")
    print(result["route"])

    print("\nResponse:")
    print(result["response"])

    return result


def main():

    # ========================================================
    # WEATHER
    # ========================================================

    result = run_query(
        "What is the current weather?"
    )

    assert result["route"] == "tool"

    assert (
        "Temperature"
        in result["response"]
    )

    # ========================================================
    # TEMPERATURE
    # ========================================================

    result = run_query(
        "What is the current temperature?"
    )

    assert result["route"] == "tool"

    assert (
        "Temperature"
        in result["response"]
    )

    # ========================================================
    # UNSUPPORTED TOOL
    # ========================================================

    result = run_query(
        "Send an email to the customer"
    )

    assert result["route"] == "tool"

    assert (
        "No approved tool"
        in result["response"]
    )

    print("\n" + "=" * 60)
    print("TOOL AGENT TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()