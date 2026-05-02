from mcpgen.core.models import RiskLevel, Tool
from mcpgen.runtime.router import rank_relevant_tools, select_relevant_tools


def test_select_relevant_tools_matches_name_and_description() -> None:
    tools = [
        Tool(name="list_customers", description="List customers", method="GET", path="/customers", risk_level=RiskLevel.LOW),
        Tool(name="list_invoices", description="List invoices", method="GET", path="/invoices", risk_level=RiskLevel.LOW),
        Tool(name="list_products", description="List products", method="GET", path="/products", risk_level=RiskLevel.LOW),
    ]

    selected = select_relevant_tools("customer invoice", tools)

    assert [tool.name for tool in selected] == ["list_customers", "list_invoices"]


def test_select_relevant_tools_returns_top_five() -> None:
    tools = [
        Tool(
            name=f"list_invoice_{index}",
            description="List invoice records",
            method="GET",
            path=f"/invoices/{index}",
            risk_level=RiskLevel.LOW,
        )
        for index in range(10)
    ]

    selected = select_relevant_tools("invoice", tools)

    assert len(selected) == 5


def test_rank_relevant_tools_explains_matches() -> None:
    tools = [
        Tool(name="list_customers", description="List customers", method="GET", path="/customers", risk_level=RiskLevel.LOW),
        Tool(name="list_invoices", description="List customer invoices", method="GET", path="/invoices", risk_level=RiskLevel.LOW),
    ]

    ranked = rank_relevant_tools("customer invoice", tools)

    assert ranked[0]["tool"].name == "list_invoices"
    assert ranked[0]["score"] == 2
    assert ranked[0]["matched_terms"] == ["customer", "invoice"]
    assert ranked[1]["tool"].name == "list_customers"
    assert ranked[1]["score"] == 1
