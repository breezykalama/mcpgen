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


def validate_tool_response(tool: dict, data) -> dict:
    """Validate response data against a generated response_schema when available."""
    response_schema = tool.get("response_schema")
    if not response_schema:
        return {
            "valid": True,
            "status": "skipped",
            "tool_name": tool.get("name", "unknown"),
            "reason": "No response_schema is available.",
            "errors": [],
        }

    errors = validate_value(data, response_schema, path="response")
    if errors:
        return {
            "valid": False,
            "status": "response_validation_error",
            "tool_name": tool.get("name", "unknown"),
            "errors": errors,
        }

    return {
        "valid": True,
        "status": "valid",
        "tool_name": tool.get("name", "unknown"),
        "errors": [],
    }


def validate_value(value, schema: dict, path: str) -> list[dict]:
    errors = []
    expected_type = schema.get("type")

    if expected_type and not value_matches_type(value, expected_type):
        return [
            {
                "field": path,
                "reason": f"expected {expected_type}",
                "received_type": type(value).__name__,
            }
        ]

    enum_values = schema.get("enum")
    if enum_values is not None and value not in enum_values:
        errors.append(
            {
                "field": path,
                "reason": "value is not in enum",
                "allowed_values": enum_values,
            }
        )

    if expected_type == "object" or isinstance(value, dict) and schema.get("properties"):
        errors.extend(validate_object(value, schema, path))

    if expected_type == "array":
        item_schema = schema.get("items") or {}
        for index, item in enumerate(value):
            errors.extend(validate_value(item, item_schema, f"{path}[{index}]"))

    return errors


def validate_object(value: dict, schema: dict, path: str) -> list[dict]:
    errors = []
    properties = schema.get("properties") or {}
    required = schema.get("required") or []

    for field in required:
        if field not in value or value[field] is None:
            errors.append(
                {
                    "field": f"{path}.{field}",
                    "reason": "required field is missing",
                }
            )

    for field, field_value in value.items():
        property_schema = properties.get(field)
        if property_schema:
            errors.extend(validate_value(field_value, property_schema, f"{path}.{field}"))

    return errors


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
