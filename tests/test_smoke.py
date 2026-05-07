from pathlib import Path

from mcpgen.core.config import MCPGenConfig
from mcpgen.core.smoke import run_smoke_test


def test_run_smoke_test_passes_for_fastapi_with_routing_cases(tmp_path: Path) -> None:
    cases_path = tmp_path / "routing_eval.yaml"
    cases_path.write_text(
        """
        - query: list invoices
          expected:
            - list_invoices
        """,
        encoding="utf-8",
    )

    result = run_smoke_test(
        Path("examples/openapi.yaml"),
        MCPGenConfig(routing_mode="keyword"),
        cases_path=cases_path,
    )

    assert result["status"] == "pass"
    assert any(check["name"] == "generated_server" and check["status"] == "pass" for check in result["checks"])
    assert any(check["name"] == "routing_eval" and check["status"] == "pass" for check in result["checks"])


def test_run_smoke_test_fails_when_no_safe_tools_are_exposed() -> None:
    result = run_smoke_test(
        Path("examples/openapi.yaml"),
        MCPGenConfig(allowed_methods=[]),
    )

    assert result["status"] == "fail"
    assert any(check["name"] == "safe_tools" and check["status"] == "fail" for check in result["checks"])


def test_run_smoke_test_supports_mcp_mode() -> None:
    result = run_smoke_test(
        Path("examples/openapi.yaml"),
        MCPGenConfig(routing_mode="keyword"),
        mode="mcp",
    )

    assert result["status"] == "pass"
    assert any("MCP server module handles tools/list" in check["message"] for check in result["checks"])
