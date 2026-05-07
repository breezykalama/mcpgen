from mcpgen.core.config import MCPGenConfig
from mcpgen.core.models import RiskLevel, Tool
from mcpgen.core.tool_selection import apply_tool_selection


def make_tool(name: str, method: str, path: str) -> Tool:
    return Tool(
        name=name,
        description=name,
        method=method,
        path=path,
        risk_level=RiskLevel.LOW if method == "GET" else RiskLevel.MEDIUM,
    )


def test_include_tools_selects_only_named_tools() -> None:
    tools = [
        make_tool("list_users", "GET", "/users"),
        make_tool("list_posts", "GET", "/posts"),
    ]

    selected, report = apply_tool_selection(tools, MCPGenConfig(include_tools=["list_users"]))

    assert [tool.name for tool in selected] == ["list_users"]
    assert report["counts"]["excluded_tools"] == 1
    assert report["excluded"][0]["reason"] == "Tool name is not listed in include_tools."


def test_exclude_paths_supports_wildcards() -> None:
    tools = [
        make_tool("list_users", "GET", "/users"),
        make_tool("list_admin_users", "GET", "/admin/users"),
    ]

    selected, report = apply_tool_selection(tools, MCPGenConfig(exclude_paths=["/admin/*"]))

    assert [tool.name for tool in selected] == ["list_users"]
    assert report["excluded"][0]["name"] == "list_admin_users"
    assert report["excluded"][0]["reason"] == "Tool path is matched by exclude_paths."


def test_include_methods_limits_selected_methods() -> None:
    tools = [
        make_tool("list_users", "GET", "/users"),
        make_tool("create_user", "POST", "/users"),
    ]

    selected, report = apply_tool_selection(tools, MCPGenConfig(include_methods=["get"]))

    assert [tool.name for tool in selected] == ["list_users"]
    assert report["policy"]["include_methods"] == ["GET"]


def test_exclude_tools_wins_after_include_filters() -> None:
    tools = [
        make_tool("list_users", "GET", "/users"),
        make_tool("list_posts", "GET", "/posts"),
    ]

    selected, report = apply_tool_selection(
        tools,
        MCPGenConfig(include_paths=["/*"], exclude_tools=["list_posts"]),
    )

    assert [tool.name for tool in selected] == ["list_users"]
    assert report["excluded"][0]["reason"] == "Tool name is listed in exclude_tools."
