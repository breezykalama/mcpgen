from mcpgen.core.models import RiskLevel, Tool
from mcpgen.runtime.safety import build_safety_report, filter_safe_tools


def test_filter_safe_tools_only_allows_enabled_low_risk_tools() -> None:
    tools = [
        Tool(name="list_users", description="List users", method="GET", path="/users", risk_level=RiskLevel.LOW),
        Tool(
            name="create_user",
            description="Create user",
            method="POST",
            path="/users",
            risk_level=RiskLevel.MEDIUM,
            enabled=False,
        ),
        Tool(
            name="delete_user",
            description="Delete user",
            method="DELETE",
            path="/users/{id}",
            risk_level=RiskLevel.HIGH,
            enabled=False,
        ),
    ]

    safe_tools = filter_safe_tools(tools)

    assert [tool.name for tool in safe_tools] == ["list_users"]


def test_build_safety_report_explains_withheld_tools() -> None:
    tools = [
        Tool(name="list_users", description="List users", method="GET", path="/users", risk_level=RiskLevel.LOW),
        Tool(
            name="delete_user",
            description="Delete user",
            method="DELETE",
            path="/users/{id}",
            risk_level=RiskLevel.HIGH,
            enabled=False,
        ),
    ]
    safe_tools = filter_safe_tools(tools)

    report = build_safety_report(tools, safe_tools)

    assert report["counts"]["withheld_tools"] == 1
    assert report["withheld"][0]["name"] == "delete_user"
    assert report["withheld"][0]["reason"] == "High-risk tools are not exposed in the MVP."
