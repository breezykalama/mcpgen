from pathlib import Path

from mcpgen.core.models import Tool


def write_tool_catalog(tools: list[Tool], safe_tools: list[Tool], path: Path) -> None:
    """Write a human-readable catalog for reviewing generated tools."""
    safe_names = {tool.name for tool in safe_tools}
    lines = [
        "# MCPGen Tool Catalog",
        "",
        "Review this file before exposing generated tools to an AI application.",
        "",
        f"Total selected tools: {len(tools)}",
        f"Exposed safe tools: {len(safe_tools)}",
        f"Withheld tools: {len(tools) - len(safe_tools)}",
        "",
    ]

    for tool in tools:
        lines.extend(render_tool(tool, exposed=tool.name in safe_names))

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def render_tool(tool: Tool, exposed: bool) -> list[str]:
    lines = [
        f"## {tool.name}",
        "",
        f"- Method: `{tool.method}`",
        f"- Path: `{tool.path}`",
        f"- Risk: `{tool.risk_level.value}`",
        f"- Exposed: `{'yes' if exposed else 'no'}`",
        f"- Enabled by default: `{'yes' if tool.enabled else 'no'}`",
        "",
        tool.description,
        "",
    ]

    input_lines = render_schema_fields(tool.input_schema)
    if input_lines:
        lines.append("### Inputs")
        lines.append("")
        lines.extend(input_lines)
        lines.append("")

    if tool.response_schema:
        response_lines = render_schema_fields(tool.response_schema)
        if response_lines:
            lines.append("### Response")
            lines.append("")
            lines.extend(response_lines)
            lines.append("")

    return lines


def render_schema_fields(schema: dict, prefix: str = "") -> list[str]:
    schema_type = schema.get("type")
    if schema_type == "array":
        item_schema = schema.get("items") or {}
        item_lines = render_schema_fields(item_schema, prefix=prefix)
        return item_lines or [f"- `{prefix or 'items'}`: array"]

    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    lines = []

    for name, property_schema in properties.items():
        field_name = f"{prefix}.{name}" if prefix else name
        field_type = property_schema.get("type", "object" if property_schema.get("properties") else "unknown")
        required_label = ", required" if name in required else ""
        lines.append(f"- `{field_name}`: {field_type}{required_label}")

        if field_type == "object" or property_schema.get("properties"):
            lines.extend(render_schema_fields(property_schema, prefix=field_name))
        elif field_type == "array":
            item_schema = property_schema.get("items") or {}
            lines.extend(render_schema_fields(item_schema, prefix=f"{field_name}[]"))

    return lines
