from mcpgen.runtime.validation import validate_tool_response


def response_tool() -> dict:
    return {
        "name": "list_users",
        "response_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "email"],
                "properties": {
                    "id": {"type": "integer"},
                    "email": {"type": "string"},
                    "active": {"type": "boolean"},
                    "role": {"type": "string", "enum": ["admin", "member"]},
                    "profile": {
                        "type": "object",
                        "required": ["displayName"],
                        "properties": {
                            "displayName": {"type": "string"},
                        },
                    },
                },
            },
        },
    }


def test_validate_tool_response_passes_valid_response() -> None:
    result = validate_tool_response(
        response_tool(),
        [
            {
                "id": 1,
                "email": "ada@example.com",
                "active": True,
                "role": "member",
                "profile": {"displayName": "Ada"},
            }
        ],
    )

    assert result["valid"] is True
    assert result["status"] == "valid"


def test_validate_tool_response_reports_nested_errors() -> None:
    result = validate_tool_response(
        response_tool(),
        [
            {
                "id": "1",
                "active": "yes",
                "role": "owner",
                "profile": {},
            }
        ],
    )

    assert result["valid"] is False
    assert result["status"] == "response_validation_error"
    assert {"field": "response[0].email", "reason": "required field is missing"} in result["errors"]
    assert any(error["field"] == "response[0].id" and error["reason"] == "expected integer" for error in result["errors"])
    assert any(error["field"] == "response[0].role" and error["reason"] == "value is not in enum" for error in result["errors"])
    assert {
        "field": "response[0].profile.displayName",
        "reason": "required field is missing",
    } in result["errors"]


def test_validate_tool_response_skips_when_schema_missing() -> None:
    result = validate_tool_response({"name": "list_users"}, [{"id": "anything"}])

    assert result["valid"] is True
    assert result["status"] == "skipped"
