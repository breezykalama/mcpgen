import re

from mcpgen.core.models import Endpoint, RiskLevel, Tool


def endpoint_to_tool(endpoint: Endpoint) -> Tool:
    """Convert one OpenAPI endpoint into an MCP-style tool descriptor."""
    method = endpoint.method.upper()
    name = build_tool_name(endpoint)

    return Tool(
        name=name,
        description=build_description(endpoint),
        method=method,
        path=endpoint.path,
        risk_level=classify_risk(method),
        enabled=method == "GET",
        operation_id=endpoint.operation_id,
        parameters=endpoint.parameters,
        request_body=endpoint.request_body,
        input_schema=build_input_schema(endpoint),
    )


def generate_tools(endpoints: list[Endpoint]) -> list[Tool]:
    return [endpoint_to_tool(endpoint) for endpoint in endpoints]


def classify_risk(method: str) -> RiskLevel:
    method = method.upper()
    if method == "GET":
        return RiskLevel.LOW
    if method == "DELETE":
        return RiskLevel.HIGH
    return RiskLevel.MEDIUM


def build_tool_name(endpoint: Endpoint) -> str:
    if endpoint.operation_id:
        return slugify(endpoint.operation_id)

    path_part = endpoint.path.strip("/").replace("/", "_").replace("{", "by_").replace("}", "")
    raw_name = f"{endpoint.method.lower()}_{path_part or 'root'}"
    return slugify(raw_name)


def build_description(endpoint: Endpoint) -> str:
    summary = endpoint.summary or endpoint.description
    if summary:
        return summary.strip()

    return f"{endpoint.method.upper()} {endpoint.path}"


def build_input_schema(endpoint: Endpoint) -> dict:
    """Build a JSON Schema input object from OpenAPI params and JSON body."""
    schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    add_parameters_to_schema(schema, endpoint.parameters)
    add_request_body_to_schema(schema, endpoint.request_body)

    if not schema["required"]:
        schema.pop("required")

    return schema


def add_parameters_to_schema(input_schema: dict, parameters: list[dict]) -> None:
    for parameter in parameters:
        name = parameter.get("name")
        if not name:
            continue

        property_schema = dict(parameter.get("schema") or {"type": "string"})
        if parameter.get("description"):
            property_schema.setdefault("description", parameter["description"])
        if parameter.get("in"):
            property_schema.setdefault("x-mcpgen-location", parameter["in"])

        input_schema["properties"][name] = property_schema
        if parameter.get("required"):
            input_schema["required"].append(name)


def add_request_body_to_schema(input_schema: dict, request_body: dict | None) -> None:
    if not request_body:
        return

    json_schema = extract_json_body_schema(request_body)
    if not json_schema:
        return

    if json_schema.get("type") == "object":
        input_schema["properties"].update(json_schema.get("properties", {}))
        input_schema["required"].extend(json_schema.get("required", []))
        return

    input_schema["properties"]["body"] = json_schema
    if request_body.get("required"):
        input_schema["required"].append("body")


def extract_json_body_schema(request_body: dict) -> dict | None:
    content = request_body.get("content") or {}
    media = content.get("application/json")
    if not media:
        return None
    schema = media.get("schema")
    if not isinstance(schema, dict):
        return None
    return schema


def slugify(value: str) -> str:
    value = split_camel_case(value)
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_").lower()


def split_camel_case(value: str) -> str:
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
