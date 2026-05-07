from pathlib import Path

from mcpgen.core.config import MCPGenConfig
from mcpgen.core.watchdog import build_watchdog_baseline, run_watchdog


def test_run_watchdog_writes_baseline(tmp_path: Path) -> None:
    baseline_path = tmp_path / "mcpgen.baseline.json"

    result = run_watchdog(
        Path("examples/openapi.yaml"),
        MCPGenConfig(routing_mode="keyword"),
        baseline_path=baseline_path,
        write_baseline=True,
    )

    assert result["status"] == "pass"
    assert baseline_path.exists()
    assert result["current"]["tool_counts"]["selected"] == 5


def test_run_watchdog_passes_when_no_drift(tmp_path: Path) -> None:
    baseline_path = tmp_path / "mcpgen.baseline.json"
    run_watchdog(
        Path("examples/openapi.yaml"),
        MCPGenConfig(routing_mode="keyword"),
        baseline_path=baseline_path,
        write_baseline=True,
    )

    result = run_watchdog(
        Path("examples/openapi.yaml"),
        MCPGenConfig(routing_mode="keyword"),
        baseline_path=baseline_path,
    )

    assert result["status"] == "pass"
    assert any(check["name"] == "baseline" and check["status"] == "pass" for check in result["checks"])


def test_run_watchdog_warns_for_added_tool(tmp_path: Path) -> None:
    baseline_path = tmp_path / "mcpgen.baseline.json"
    current = build_watchdog_baseline(Path("examples/openapi.yaml"), MCPGenConfig())
    current["tools"] = [tool for tool in current["tools"] if tool["name"] != "list_invoices"]
    baseline_path.write_text(__import__("json").dumps(current), encoding="utf-8")

    result = run_watchdog(
        Path("examples/openapi.yaml"),
        MCPGenConfig(routing_mode="keyword"),
        baseline_path=baseline_path,
    )

    assert result["status"] == "warn"
    assert any(check["name"] == "tool_added" and "list_invoices" in check["message"] for check in result["checks"])


def test_run_watchdog_fails_for_removed_tool(tmp_path: Path) -> None:
    baseline_path = tmp_path / "mcpgen.baseline.json"
    current = build_watchdog_baseline(Path("examples/openapi.yaml"), MCPGenConfig())
    current["tools"].append(
        {
            "name": "missing_tool",
            "method": "GET",
            "path": "/missing",
            "risk_level": "low",
            "exposed": True,
            "input_schema": {},
            "response_schema": None,
        }
    )
    baseline_path.write_text(__import__("json").dumps(current), encoding="utf-8")

    result = run_watchdog(
        Path("examples/openapi.yaml"),
        MCPGenConfig(routing_mode="keyword"),
        baseline_path=baseline_path,
    )

    assert result["status"] == "fail"
    assert any(check["name"] == "tool_removed" and "missing_tool" in check["message"] for check in result["checks"])


def test_run_watchdog_fails_for_schema_drift(tmp_path: Path) -> None:
    baseline_path = tmp_path / "mcpgen.baseline.json"
    current = build_watchdog_baseline(Path("examples/openapi.yaml"), MCPGenConfig())
    current["tools"][0]["input_schema"] = {"type": "object", "properties": {"changed": {"type": "string"}}}
    baseline_path.write_text(__import__("json").dumps(current), encoding="utf-8")

    result = run_watchdog(
        Path("examples/openapi.yaml"),
        MCPGenConfig(routing_mode="keyword"),
        baseline_path=baseline_path,
    )

    assert result["status"] == "fail"
    assert any(check["name"] == "tool_input_schema_changed" for check in result["checks"])
