def validate_tool_inputs(tool: dict, inputs: dict | None) -> dict:
    """Validate inputs against the generated tool input schema."""
    input_schema = tool.get("input_schema") or {}
    properties = input_schema.get("properties") or {}
    required = input_schema.get("required") or []
    values = inputs or {}
    errors = []

    for field in required:
        if field not in values or values[field] is None:
            errors.append(
                {
                    "field": field,
                    "reason": "required field is missing",
                }
            )

    for field, value in values.items():
        property_schema = properties.get(field)
        if not property_schema:
            continue

        expected_type = property_schema.get("type")
        if expected_type and not value_matches_type(value, expected_type):
            errors.append(
                {
                    "field": field,
                    "reason": f"expected {expected_type}",
                    "received_type": type(value).__name__,
                }
            )
            continue

        enum_values = property_schema.get("enum")
        if enum_values is not None and value not in enum_values:
            errors.append(
                {
                    "field": field,
                    "reason": "value is not in enum",
                    "allowed_values": enum_values,
                }
            )

    if errors:
        return {
            "valid": False,
            "status": "validation_error",
            "tool_name": tool.get("name", "unknown"),
            "errors": errors,
        }

    return {
        "valid": True,
        "status": "valid",
        "tool_name": tool.get("name", "unknown"),
        "errors": [],
    }


def value_matches_type(value, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    return True
