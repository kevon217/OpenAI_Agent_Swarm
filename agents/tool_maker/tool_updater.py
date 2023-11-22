def normalize_tool(tool):
    """Normalize a tool to a comparable dictionary format."""
    if isinstance(tool, dict):
        return tool  # Assuming JSON tools are already in the correct format
    elif hasattr(tool, "type"):
        normalized = {"type": tool.type}
        if hasattr(tool, "function"):
            normalized["function"] = tool.function
        return normalized
    else:
        return {}  # Unknown tool format
