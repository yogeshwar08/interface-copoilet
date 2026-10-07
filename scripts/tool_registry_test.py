from app.tools.registry import (
    get_tool,
    list_tools,
)


def main():

    print("=" * 60)
    print("TOOL REGISTRY TEST")
    print("=" * 60)

    # ========================================================
    # LIST APPROVED TOOLS
    # ========================================================

    tools = list_tools()

    print("\nApproved tools:")

    for tool in tools:

        print(
            f"- {tool['name']}: "
            f"{tool['description']}"
        )

    # ========================================================
    # VALID TOOL
    # ========================================================

    weather = get_tool("weather")

    assert weather.name == "weather"

    print("\nValid tool lookup:")
    print("weather -> ALLOWED")

    # ========================================================
    # INVALID TOOL
    # ========================================================

    try:

        get_tool("delete_database")

        raise AssertionError(
            "Unauthorized tool was allowed!"
        )

    except ValueError as exc:

        print("\nInvalid tool lookup:")
        print("delete_database -> BLOCKED")
        print(f"Reason: {exc}")

    print("\n" + "=" * 60)
    print("TOOL REGISTRY TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()