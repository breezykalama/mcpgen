from collections import Counter
from pathlib import Path

from mcpgen.core.config import MCPGenConfig
from mcpgen.core.models import RiskLevel
from mcpgen.core.parser import parse_openapi
from mcpgen.core.tool_generator import generate_tools
from mcpgen.runtime.safety import build_safety_report, filter_safe_tools


def inspect_spec(spec_path: Path, config: MCPGenConfig | None = None) -> dict:
    """Inspect an OpenAPI spec without writing generated files."""
    config = config or MCPGenConfig()
    all_tools = generate_tools(parse_openapi(spec_path))
    safe_tools = filter_safe_tools(all_tools, allowed_methods=config.normalized_allowed_methods())
    safety_report = build_safety_report(
        all_tools,
        safe_tools,
        allowed_methods=config.normalized_allowed_methods(),
    )

    risk_counts = Counter(tool.risk_level for tool in all_tools)

    return {
        "total_tools": len(all_tools),
        "exposed_tools": len(safe_tools),
        "withheld_tools": len(all_tools) - len(safe_tools),
        "risk_breakdown": {
            RiskLevel.LOW.value: risk_counts[RiskLevel.LOW],
            RiskLevel.MEDIUM.value: risk_counts[RiskLevel.MEDIUM],
            RiskLevel.HIGH.value: risk_counts[RiskLevel.HIGH],
        },
        "exposed": [tool.name for tool in safe_tools],
        "withheld": safety_report["withheld"],
        "policy": safety_report["policy"],
    }
