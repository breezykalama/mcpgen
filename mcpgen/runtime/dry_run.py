from urllib.parse import urlencode

from mcpgen.core.models import Tool


def build_dry_run_request(tool: Tool, inputs: dict, api_base_url: str) -> dict:
    """Build a request preview without executing any network call."""
    path = tool.path
    query_params = {}
    body = {}

    for name, value in inputs.items():
        location = input_location(tool, name)
        if location == "path":
            path = path.replace(f"{{{name}}}", str(value))
        elif location == "query":
            query_params[name] = value
        else:
            body[name] = value

    url = build_url(api_base_url, path, query_params)
    preview = {
        "tool": tool.name,
        "method": tool.method,
        "url": url,
        "executed": False,
    }

    if body and tool.method.upper() != "GET":
        preview["json"] = body

    return preview


def input_location(tool: Tool, name: str) -> str:
    property_schema = tool.input_schema.get("properties", {}).get(name, {})
    return property_schema.get("x-mcpgen-location", "body")


def build_url(api_base_url: str, path: str, query_params: dict) -> str:
    base = api_base_url.rstrip("/")
    route = path if path.startswith("/") else f"/{path}"
    url = f"{base}{route}"

    if query_params:
        url = f"{url}?{urlencode(query_params)}"

    return url
