from mcpgen.core.models import Endpoint, RiskLevel
from mcpgen.core.tool_generator import classify_risk, endpoint_to_tool


def test_classify_risk_by_method() -> None:
    assert classify_risk("GET") == RiskLevel.LOW
    assert classify_risk("POST") == RiskLevel.MEDIUM
    assert classify_risk("PUT") == RiskLevel.MEDIUM
    assert classify_risk("PATCH") == RiskLevel.MEDIUM
    assert classify_risk("DELETE") == RiskLevel.HIGH


def test_endpoint_to_tool_uses_snake_case_names_and_metadata() -> None:
    endpoint = Endpoint(
        operation_id="listCustomerInvoices",
        summary="List customer invoices",
        method="GET",
        path="/customers/{customerId}/invoices",
        parameters=[{"name": "customerId", "in": "path", "required": True}],
    )

    tool = endpoint_to_tool(endpoint)

    assert tool.name == "list_customer_invoices"
    assert tool.operation_id == "listCustomerInvoices"
    assert tool.parameters[0]["name"] == "customerId"
    assert tool.input_schema == {
        "type": "object",
        "properties": {
            "customerId": {
                "type": "string",
                "x-mcpgen-location": "path",
            }
        },
        "required": ["customerId"],
    }
    assert tool.risk_level == RiskLevel.LOW
    assert tool.enabled is True


def test_write_actions_are_disabled_by_default() -> None:
    endpoint = Endpoint(
        operation_id="createInvoice",
        summary="Create invoice",
        method="POST",
        path="/invoices",
        request_body={"content": {"application/json": {"schema": {"type": "object"}}}},
    )

    tool = endpoint_to_tool(endpoint)

    assert tool.name == "create_invoice"
    assert tool.risk_level == RiskLevel.MEDIUM
    assert tool.enabled is False
    assert tool.request_body is not None


def test_request_body_object_schema_becomes_input_schema() -> None:
    endpoint = Endpoint(
        operation_id="createInvoice",
        summary="Create invoice",
        method="POST",
        path="/invoices",
        request_body={
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["customerId", "amount"],
                        "properties": {
                            "customerId": {"type": "string"},
                            "amount": {"type": "number"},
                        },
                    }
                }
            },
        },
    )

    tool = endpoint_to_tool(endpoint)

    assert tool.input_schema == {
        "type": "object",
        "properties": {
            "customerId": {"type": "string"},
            "amount": {"type": "number"},
        },
        "required": ["customerId", "amount"],
    }


def test_endpoint_to_tool_extracts_response_schema() -> None:
    endpoint = Endpoint(
        operation_id="getInvoice",
        summary="Get invoice",
        method="GET",
        path="/invoices/{invoiceId}",
        responses={
            "200": {
                "description": "Invoice",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "invoiceId": {"type": "string"},
                                "amount": {"type": "number"},
                            },
                        }
                    }
                },
            }
        },
    )

    tool = endpoint_to_tool(endpoint)

    assert tool.response_schema == {
        "type": "object",
        "properties": {
            "invoiceId": {"type": "string"},
            "amount": {"type": "number"},
        },
    }
