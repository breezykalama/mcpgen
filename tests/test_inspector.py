from pathlib import Path

from mcpgen.core.inspector import inspect_spec


def test_inspect_spec_returns_risk_and_safety_summary() -> None:
    result = inspect_spec(Path("examples/openapi.yaml"))

    assert result["total_tools"] == 5
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
