from fnmatch import fnmatch

from mcpgen.core.models import Tool


def apply_tool_selection(tools: list[Tool], config: object) -> tuple[list[Tool], dict]:
    """Apply developer-controlled include/exclude filters before safety filtering."""
    selected = []
    excluded = []

    for tool in tools:
        reason = exclusion_reason(tool, config)
        if reason:
            excluded.append(
                {
                    "name": tool.name,
                    "method": tool.method,
                    "path": tool.path,
                    "reason": reason,
                }
            )
            continue
        selected.append(tool)

    report = {
        "policy": {
            "include_tools": list(getattr(config, "include_tools", [])),
            "exclude_tools": list(getattr(config, "exclude_tools", [])),
            "include_paths": list(getattr(config, "include_paths", [])),
            "exclude_paths": list(getattr(config, "exclude_paths", [])),
            "include_methods": sorted(normalized_methods(getattr(config, "include_methods", []))),
            "exclude_methods": sorted(normalized_methods(getattr(config, "exclude_methods", []))),
        },
        "counts": {
            "discovered_tools": len(tools),
            "selected_tools": len(selected),
            "excluded_tools": len(excluded),
        },
        "selected": [tool.name for tool in selected],
        "excluded": excluded,
    }
    return selected, report


def exclusion_reason(tool: Tool, config: object) -> str | None:
    include_tools = set(getattr(config, "include_tools", []))
    exclude_tools = set(getattr(config, "exclude_tools", []))
    include_paths = list(getattr(config, "include_paths", []))
    exclude_paths = list(getattr(config, "exclude_paths", []))
    include_methods = normalized_methods(getattr(config, "include_methods", []))
    exclude_methods = normalized_methods(getattr(config, "exclude_methods", []))
    method = tool.method.upper()

    if include_tools and tool.name not in include_tools:
        return "Tool name is not listed in include_tools."
    if include_paths and not matches_any(tool.path, include_paths):
        return "Tool path is not matched by include_paths."
    if include_methods and method not in include_methods:
        return "Tool method is not listed in include_methods."
    if tool.name in exclude_tools:
        return "Tool name is listed in exclude_tools."
    if matches_any(tool.path, exclude_paths):
        return "Tool path is matched by exclude_paths."
    if method in exclude_methods:
        return "Tool method is listed in exclude_methods."

    return None


def matches_any(value: str, patterns: list[str]) -> bool:
    return any(fnmatch(value, pattern) for pattern in patterns)


def normalized_methods(methods: list[str]) -> set[str]:
    return {method.upper() for method in methods}
