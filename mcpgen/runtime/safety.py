from mcpgen.core.models import RiskLevel, Tool


def filter_safe_tools(tools: list[Tool], allowed_methods: set[str] | None = None) -> list[Tool]:
    """MVP safety policy: expose only enabled low-risk tools."""
    allowed = allowed_methods or {"GET"}
    return [
        tool
        for tool in tools
        if tool.enabled and tool.risk_level == RiskLevel.LOW and tool.method.upper() in allowed
    ]


def build_safety_report(tools: list[Tool], safe_tools: list[Tool], allowed_methods: set[str] | None = None) -> dict:
    """Explain which tools were exposed or withheld by the safety layer."""
    allowed = allowed_methods or {"GET"}
    safe_names = {tool.name for tool in safe_tools}

    return {
        "policy": {
            "allowed_methods": sorted(allowed),
            "exposes_only_low_risk": True,
            "write_actions_disabled_by_default": True,
            "high_risk_tools_exposed": False,
        },
        "counts": {
            "total_tools": len(tools),
            "exposed_tools": len(safe_tools),
            "withheld_tools": len(tools) - len(safe_tools),
        },
        "exposed": [tool.name for tool in safe_tools],
        "withheld": [
            {
                "name": tool.name,
                "method": tool.method,
                "path": tool.path,
                "risk_level": tool.risk_level.value,
                "reason": disabled_reason(tool, allowed),
            }
            for tool in tools
            if tool.name not in safe_names
        ],
    }


def disabled_reason(tool: Tool, allowed_methods: set[str]) -> str:
    if tool.risk_level == RiskLevel.HIGH:
        return "High-risk tools are not exposed in the MVP."
    if not tool.enabled:
        return "Write actions are disabled by default."
    if tool.method.upper() not in allowed_methods:
        return "HTTP method is not allowed by config."
    if tool.risk_level != RiskLevel.LOW:
        return "Only low-risk tools are exposed in the MVP."
    return "Tool was withheld by the safety policy."
