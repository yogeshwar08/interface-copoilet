from app.tools.registry import get_tool


def main():

    print("=" * 60)
    print("TOOL DISPATCHER SECURITY TEST")
    print("=" * 60)

    # ========================================================
    # APPROVED TOOL
    # ========================================================

    weather = get_tool("weather")

    assert weather.name == "weather"

    print("\nApproved tool:")
    print("weather -> ALLOWED")

    # ========================================================
    # UNAUTHORIZED TOOLS
    # ========================================================

    unauthorized_tools = [
        "delete_database",
        "drop_table",
        "execute_python",
        "send_email",
        "shell",
        "arbitrary_url",
    ]

    for tool_name in unauthorized_tools:

        try:

            get_tool(tool_name)

            raise AssertionError(
                f"Unauthorized tool allowed: "
                f"{tool_name}"
            )

        except ValueError:

            print(
                f"{tool_name} -> BLOCKED"
            )

    print("\n" + "=" * 60)
    print("TOOL DISPATCHER SECURITY TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()