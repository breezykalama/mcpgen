import random


def should_use_mock(config: dict) -> bool:
    mock_config = config.get("mock") or {}
    return mock_config.get("enabled") is True


def build_mock_response(tool: dict, params: dict, config: dict) -> dict:
    """Build a deterministic mock response for a tool."""
    mock_config = config.get("mock") or {}
    seed = int(mock_config.get("seed", 123))
    list_size = int(mock_config.get("list_size", 3))
    data = build_mock_data(tool, params, seed=seed, list_size=list_size)

    return {
        "tool": tool.get("name", "unknown"),
        "status": "success",
        "status_code": 200,
        "data": data,
        "mocked": True,
    }


def build_mock_data(tool: dict, params: dict, seed: int, list_size: int):
    response_schema = tool.get("response_schema")
    if response_schema:
        return build_mock_from_schema(response_schema, params, seed, list_size, index=1)

    if looks_like_list_tool(tool):
        return [build_mock_object(tool, params, seed + index, index=index + 1) for index in range(list_size)]

    return build_mock_object(tool, params, seed, index=1)


def looks_like_list_tool(tool: dict) -> bool:
    name = tool.get("name", "")
    path = tool.get("path", "").rstrip("/")
    return name.startswith("list_") or "list" in name or "{" not in path


def build_mock_object(tool: dict, params: dict, seed: int, index: int) -> dict:
    rng = random.Random(seed)
    properties = (tool.get("input_schema") or {}).get("properties") or {}
    output = {
        "id": params.get("id", index),
    }

    for name, schema in properties.items():
        if name in output:
            continue
        if name in params:
            output[name] = params[name]
        else:
            output[name] = mock_value(name, schema, rng, index)

    resource_name = infer_resource_name(tool)
    output.setdefault("name", f"{resource_name.title()} {index}")
    output.setdefault("mock", True)
    return output


def build_mock_from_schema(schema: dict, params: dict, seed: int, list_size: int, index: int):
    schema_type = schema.get("type", "object")
    rng = random.Random(seed + index)

    if schema_type == "array":
        item_schema = schema.get("items") or {"type": "object"}
        return [
            build_mock_from_schema(item_schema, params, seed + item_index, list_size, index=item_index + 1)
            for item_index in range(list_size)
        ]

    if schema_type == "object" or "properties" in schema:
        output = {}
        for name, property_schema in (schema.get("properties") or {}).items():
            if name in params:
                output[name] = params[name]
            else:
                output[name] = mock_value(name, property_schema, rng, index)
        output.setdefault("mock", True)
        return output

    return mock_value("value", schema, rng, index)


def mock_value(name: str, schema: dict, rng: random.Random, index: int):
    schema_type = schema.get("type", "string")
    enum_values = schema.get("enum")
    if enum_values:
        return enum_values[0]
    if schema_type == "integer":
        return index
    if schema_type == "number":
        return round(rng.random() * 100, 2)
    if schema_type == "boolean":
        return index % 2 == 0
    if schema_type == "array":
        item_schema = schema.get("items") or {"type": "string"}
        return [mock_value(name, item_schema, rng, index)]
    if schema_type == "object":
        return {
            property_name: mock_value(property_name, property_schema, rng, index)
            for property_name, property_schema in (schema.get("properties") or {}).items()
        }
    return f"{name}_{index}"


def infer_resource_name(tool: dict) -> str:
    path = tool.get("path", "").strip("/")
    if not path:
        return "resource"
    first_segment = path.split("/")[0]
    return first_segment.replace("-", " ").replace("_", " ")
