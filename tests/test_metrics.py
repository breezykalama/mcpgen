import json
from pathlib import Path

import httpx

from mcpgen.core.models import RiskLevel, Tool
from mcpgen.runtime.executor import execute_tool
from mcpgen.runtime.metrics import read_metrics, record_metric
from mcpgen.runtime.policy import evaluate_tool_policy
from mcpgen.runtime.router import rank_relevant_tools


def metrics_config(tmp_path: Path) -> dict:
    return {
        "metrics_enabled": True,
        "metrics_path": str(tmp_path / "logs" / "metrics.json"),
    }


def list_invoice_tool_dict() -> dict:
    return {
        "name": "list_invoices",
        "description": "List invoices",
        "method": "GET",
        "path": "/invoices",
        "risk_level": "low",
        "input_schema": {"type": "object", "properties": {}},
    }


def test_metrics_file_is_created(tmp_path: Path) -> None:
    config = metrics_config(tmp_path)

    record_metric({"action": "dry_run", "tool_name": "list_invoices"}, config)

    assert (tmp_path / "logs" / "metrics.json").exists()
    metrics = read_metrics(config)
    assert metrics["total_dry_runs"] == 1
    assert metrics["per_tool"]["list_invoices"]["dry_runs"] == 1


def test_routing_increments_counts(tmp_path: Path) -> None:
    config = {**metrics_config(tmp_path), "routing_mode": "keyword"}
    tools = [
        Tool(name="list_invoices", description="List invoices", method="GET", path="/invoices", risk_level=RiskLevel.LOW),
        Tool(name="list_customers", description="List customers", method="GET", path="/customers", risk_level=RiskLevel.LOW),
    ]

    rank_relevant_tools("invoice", tools, config=config, routing_mode="keyword")

    metrics = read_metrics(config)
    assert metrics["total_tool_routes"] == 1
    assert metrics["per_tool"]["list_invoices"]["routed"] == 1
    assert metrics["per_tool"]["list_invoices"]["last_routing_mode"] == "keyword"


def test_policy_allowed_increments_counts(tmp_path: Path) -> None:
    config = metrics_config(tmp_path)

    evaluate_tool_policy(list_invoice_tool_dict(), config)

    metrics = read_metrics(config)
    assert metrics["total_policy_evaluations"] == 1
    assert metrics["per_tool"]["list_invoices"]["policy_allowed"] == 1


def test_policy_blocked_and_confirmation_required_increment_counts(tmp_path: Path) -> None:
    config = {
        **metrics_config(tmp_path),
        "enabled_tools": ["create_invoice"],
    }

    evaluate_tool_policy({"name": "delete_invoice", "method": "DELETE", "risk_level": "high"}, config)
    evaluate_tool_policy(
        {"name": "create_invoice", "method": "POST", "risk_level": "medium"},
        config,
        mode="safe-execute",
    )

    metrics = read_metrics(config)
    assert metrics["total_policy_evaluations"] == 2
    assert metrics["total_confirmation_required"] == 1
    assert metrics["per_tool"]["delete_invoice"]["policy_blocked"] == 1
    assert metrics["per_tool"]["create_invoice"]["policy_blocked"] == 1


def test_execution_success_increments_counts_and_latency(monkeypatch, tmp_path: Path) -> None:
    def fake_get(url, timeout):
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    config = {
        **metrics_config(tmp_path),
        "tools": [list_invoice_tool_dict()],
        "api_base_url": "https://api.example.test",
        "execution_mode": "safe-execute",
        "audit_enabled": False,
    }

    execute_tool("list_invoices", {}, config)

    metrics = read_metrics(config)
    tool_metrics = metrics["per_tool"]["list_invoices"]
    assert metrics["total_executions"] == 1
    assert metrics["total_execution_success"] == 1
    assert tool_metrics["executions"] == 1
    assert tool_metrics["successes"] == 1
    assert tool_metrics["average_execution_latency_ms"] >= 0


def test_execution_error_increments_counts_and_latency(monkeypatch, tmp_path: Path) -> None:
    def fake_get(url, timeout):
        raise httpx.ConnectError("network unavailable", request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    config = {
        **metrics_config(tmp_path),
        "tools": [list_invoice_tool_dict()],
        "api_base_url": "https://api.example.test",
        "execution_mode": "safe-execute",
        "audit_enabled": False,
    }

    execute_tool("list_invoices", {}, config)

    metrics = read_metrics(config)
    tool_metrics = metrics["per_tool"]["list_invoices"]
    assert metrics["total_executions"] == 1
    assert metrics["total_execution_errors"] == 1
    assert tool_metrics["errors"] == 1
    assert tool_metrics["average_execution_latency_ms"] >= 0


def test_metrics_disabled_writes_nothing(tmp_path: Path) -> None:
    config = {
        "metrics_enabled": False,
        "metrics_path": str(tmp_path / "logs" / "metrics.json"),
    }

    record_metric({"action": "dry_run", "tool_name": "list_invoices"}, config)

    assert not (tmp_path / "logs" / "metrics.json").exists()


def test_metrics_json_is_valid(tmp_path: Path) -> None:
    config = metrics_config(tmp_path)

    record_metric({"action": "execution_blocked", "tool_name": "delete_invoice"}, config)

    data = json.loads((tmp_path / "logs" / "metrics.json").read_text(encoding="utf-8"))
    assert data["total_execution_blocked"] == 1
    assert data["per_tool"]["delete_invoice"]["blocked"] == 1
