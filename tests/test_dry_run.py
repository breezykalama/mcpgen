from mcpgen.core.models import RiskLevel, Tool
from mcpgen.runtime.dry_run import build_dry_run_request


def test_build_dry_run_request_replaces_path_and_query_params() -> None:
    tool = Tool(
        name="list_customer_invoices",
        description="List customer invoices",
        method="GET",
        path="/customers/{customerId}/invoices",
        risk_level=RiskLevel.LOW,
        input_schema={
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "x-mcpgen-location": "path"},
                "status": {"type": "string", "x-mcpgen-location": "query"},
            },
            "required": ["customerId"],
        },
    )

    preview = build_dry_run_request(
        tool,
        {"customerId": "cus_123", "status": "open"},
        "https://api.example.com/",
    )

    assert preview == {
        "tool": "list_customer_invoices",
        "method": "GET",
        "url": "https://api.example.com/customers/cus_123/invoices?status=open",
        "executed": False,
    }
