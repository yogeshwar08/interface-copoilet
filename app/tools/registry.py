from app.tools.weather import weather_tool


# ============================================================
# APPROVED TOOL REGISTRY
# ============================================================

TOOLS = {
    weather_tool.name: weather_tool,
}


# ============================================================
# TOOL LOOKUP
# ============================================================

def get_tool(tool_name: str):

    if tool_name not in TOOLS:

        raise ValueError(
            f"Tool '{tool_name}' is not allowed."
        )

    return TOOLS[tool_name]


# ============================================================
# AVAILABLE TOOLS
# ============================================================

def list_tools():

    return [
        {
            "name": tool.name,
            "description": tool.description,
        }
        for tool in TOOLS.values()
    ]