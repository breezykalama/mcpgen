from collections import Counter
from pathlib import Path

from mcpgen.core.config import MCPGenConfig
from mcpgen.core.models import RiskLevel
from mcpgen.core.parser import find_unresolved_refs, parse_openapi
from mcpgen.core.tool_selection import apply_tool_selection
from mcpgen.core.tool_generator import generate_tools
from mcpgen.runtime.safety import build_safety_report, filter_safe_tools


def inspect_spec(spec_path: Path, config: MCPGenConfig | None = None) -> dict:
    """Inspect an OpenAPI spec without writing generated files."""
    config = config or MCPGenConfig()
    endpoints = parse_openapi(spec_path)
    discovered_tools = generate_tools(endpoints)
    selected_tools, selection_report = apply_tool_selection(discovered_tools, config)
    safe_tools = filter_safe_tools(selected_tools, allowed_methods=config.normalized_allowed_methods())
    safety_report = build_safety_report(
        selected_tools,
        safe_tools,
        allowed_methods=config.normalized_allowed_methods(),
    )
    safety_report["selection"] = selection_report

    risk_counts = Counter(tool.risk_level for tool in selected_tools)

    return {
        "total_tools": len(discovered_tools),
        "selected_tools": len(selected_tools),
        "excluded_tools": len(selection_report["excluded"]),
        "exposed_tools": len(safe_tools),
        "withheld_tools": len(selected_tools) - len(safe_tools),
        "risk_breakdown": {
            RiskLevel.LOW.value: risk_counts[RiskLevel.LOW],
            RiskLevel.MEDIUM.value: risk_counts[RiskLevel.MEDIUM],
            RiskLevel.HIGH.value: risk_counts[RiskLevel.HIGH],
        },
        "exposed": [tool.name for tool in safe_tools],
        "excluded": selection_report["excluded"],
        "selection": selection_report,
        "unresolved_refs": unresolved_refs_for_endpoints(endpoints),
        "withheld": safety_report["withheld"],
        "policy": safety_report["policy"],
    }


def unresolved_refs_for_endpoints(endpoints: list) -> list[str]:
    refs = []
    for endpoint in endpoints:
        refs.extend(find_unresolved_refs(endpoint.parameters))
        refs.extend(find_unresolved_refs(endpoint.request_body))
        refs.extend(find_unresolved_refs(endpoint.responses))
    return sorted(set(refs))
