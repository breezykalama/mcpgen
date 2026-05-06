from mcpgen.runtime.validation import validate_tool_inputs


def tool_schema() -> dict:
    return {
        "name": "get_user_by_id",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "x-mcpgen-location": "path"},
                "include": {"type": "string", "enum": ["profile", "posts"]},
                "active": {"type": "boolean"},
                "tags": {"type": "array"},
            },
            "required": ["id"],
        },
    }


def test_validation_passes_valid_inputs() -> None:
    result = validate_tool_inputs(
        tool_schema(),
        {"id": 1, "include": "profile", "active": True, "tags": ["admin"]},
    )

    assert result == {
        "valid": True,
        "status": "valid",
        "tool_name": "get_user_by_id",
        "errors": [],
    }


def test_validation_reports_missing_required_field() -> None:
    result = validate_tool_inputs(tool_schema(), {"include": "profile"})

    assert result["valid"] is False
    assert result["status"] == "validation_error"
    assert result["errors"][0] == {
        "field": "id",
        "reason": "required field is missing",
    }


def test_validation_reports_type_mismatch() -> None:
    result = validate_tool_inputs(tool_schema(), {"id": "1"})

    assert result["valid"] is False
    assert result["errors"][0]["field"] == "id"
    assert result["errors"][0]["reason"] == "expected integer"
    assert result["errors"][0]["received_type"] == "str"


def test_validation_reports_enum_mismatch() -> None:
    result = validate_tool_inputs(tool_schema(), {"id": 1, "include": "billing"})

    assert result["valid"] is False
    assert result["errors"][0]["field"] == "include"
    assert result["errors"][0]["reason"] == "value is not in enum"
    assert result["errors"][0]["allowed_values"] == ["profile", "posts"]


def test_validation_ignores_unknown_inputs() -> None:
    result = validate_tool_inputs(tool_schema(), {"id": 1, "extra": "ok"})

    assert result["valid"] is True
