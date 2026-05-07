from pathlib import Path

from mcpgen.core.catalog import write_tool_catalog
from mcpgen.core.models import RiskLevel, Tool


def test_write_tool_catalog_documents_exposed_and_withheld_tools(tmp_path: Path) -> None:
    safe_tool = Tool(
        name="list_users",
        description="List users",
        method="GET",
        path="/users",
        risk_level=RiskLevel.LOW,
        input_schema={
            "type": "object",
            "properties": {
                "active": {"type": "boolean"},
            },
        },
        response_schema={
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            },
        },
    )
    write_tool = Tool(
        name="create_user",
        description="Create user",
        method="POST",
        path="/users",
        risk_level=RiskLevel.MEDIUM,
        enabled=False,
    )

    catalog_path = tmp_path / "tool_catalog.md"
    write_tool_catalog([safe_tool, write_tool], [safe_tool], catalog_path)

    content = catalog_path.read_text(encoding="utf-8")

    assert "# MCPGen Tool Catalog" in content
    assert "## list_users" in content
    assert "- Exposed: `yes`" in content
    assert "- `active`: boolean" in content
    assert "- `id`: integer" in content
    assert "## create_user" in content
    assert "- Exposed: `no`" in content
