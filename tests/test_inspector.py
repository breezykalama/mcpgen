from pathlib import Path

from mcpgen.core.config import MCPGenConfig
from mcpgen.core.inspector import inspect_spec


def test_inspect_spec_returns_risk_and_safety_summary() -> None:
    result = inspect_spec(Path("examples/openapi.yaml"))

    assert result["total_tools"] == 5
    assert result["selected_tools"] == 5
    assert result["excluded_tools"] == 0
    assert result["exposed_tools"] == 2
    assert result["withheld_tools"] == 3
    assert result["risk_breakdown"] == {
        "low": 2,
        "medium": 2,
        "high": 1,
    }
    assert result["exposed"] == ["list_customers", "list_invoices"]
    assert [tool["name"] for tool in result["withheld"]] == [
        "create_customer",
        "create_invoice",
        "delete_invoice",
    ]


def test_inspect_spec_reports_tool_selection() -> None:
    result = inspect_spec(
        Path("examples/openapi.yaml"),
        config=MCPGenConfig(exclude_tools=["list_customers"]),
    )

    assert result["total_tools"] == 5
    assert result["selected_tools"] == 4
    assert result["excluded_tools"] == 1
    assert result["exposed_tools"] == 1
    assert result["excluded"][0]["name"] == "list_customers"
    assert result["selection"]["counts"]["excluded_tools"] == 1
