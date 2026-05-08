from pathlib import Path

import httpx

from mcpgen.runtime.circuit_breaker import (
    check_circuit_breaker,
    record_circuit_failure,
    record_circuit_success,
    reset_circuit_breakers,
)
from mcpgen.runtime.executor import execute_tool
from mcpgen.runtime.metrics import read_metrics


def config(enabled: bool = True) -> dict:
    return {
        "circuit_breaker": {
            "enabled": enabled,
            "failure_threshold": 2,
            "recovery_seconds": 60,
        }
    }


def list_tool() -> dict:
    return {
        "name": "list_invoices",
        "description": "List invoices",
        "method": "GET",
        "path": "/invoices",
        "risk_level": "low",
        "input_schema": {"type": "object", "properties": {}},
    }


def execution_config(tmp_path: Path) -> dict:
    return {
        **config(enabled=True),
        "tools": [list_tool()],
        "api_base_url": "https://api.example.test",
        "execution_mode": "safe-execute",
        "audit_enabled": True,
        "audit_log_path": str(tmp_path / "logs" / "audit.log"),
        "metrics_enabled": True,
        "metrics_path": str(tmp_path / "logs" / "metrics.json"),
    }


def test_disabled_circuit_breaker_allows_execution() -> None:
    reset_circuit_breakers()

    assert check_circuit_breaker("list_invoices", config(enabled=False))["allowed"] is True


def test_failures_open_circuit_and_success_closes_it() -> None:
    reset_circuit_breakers()

    first = record_circuit_failure("list_invoices", config())
    second = record_circuit_failure("list_invoices", config())
    blocked = check_circuit_breaker("list_invoices", config())
    closed = record_circuit_success("list_invoices", config())
    allowed = check_circuit_breaker("list_invoices", config())

    assert first["state"] == "closed"
    assert second["state"] == "open"
    assert blocked["allowed"] is False
    assert blocked["state"] == "open"
    assert closed["state"] == "closed"
    assert allowed["allowed"] is True


def test_open_circuit_blocks_execution_before_http(monkeypatch, tmp_path: Path) -> None:
    reset_circuit_breakers()
    called = False

    def fake_get(url, headers, timeout):
        nonlocal called
        called = True
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    cfg = execution_config(tmp_path)
    record_circuit_failure("list_invoices", cfg)
    record_circuit_failure("list_invoices", cfg)

    result = execute_tool("list_invoices", {}, cfg)

    assert called is False
    assert result["status_code"] == 503
    assert result["data"]["state"] == "open"
    audit_text = (tmp_path / "logs" / "audit.log").read_text(encoding="utf-8")
    assert "circuit_blocked" in audit_text
    metrics = read_metrics(cfg)
    assert metrics["total_circuit_blocked"] == 1
    assert metrics["per_tool"]["list_invoices"]["circuit_blocked"] == 1


def test_execution_errors_open_circuit_and_record_metrics(monkeypatch, tmp_path: Path) -> None:
    reset_circuit_breakers()

    def fake_get(url, headers, timeout):
        raise httpx.ConnectError("network unavailable", request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    cfg = execution_config(tmp_path)

    execute_tool("list_invoices", {}, cfg)
    execute_tool("list_invoices", {}, cfg)

    decision = check_circuit_breaker("list_invoices", cfg)
    metrics = read_metrics(cfg)
    audit_text = (tmp_path / "logs" / "audit.log").read_text(encoding="utf-8")

    assert decision["allowed"] is False
    assert metrics["total_circuit_opened"] == 1
    assert metrics["per_tool"]["list_invoices"]["circuit_opened"] == 1
    assert "circuit_opened" in audit_text


def test_recovery_window_allows_half_open_trial(monkeypatch) -> None:
    reset_circuit_breakers()
    cfg = {"circuit_breaker": {"enabled": True, "failure_threshold": 1, "recovery_seconds": 60}}
    record_circuit_failure("list_invoices", cfg)

    monkeypatch.setattr("mcpgen.runtime.circuit_breaker.time", lambda: 9999999999.0)

    decision = check_circuit_breaker("list_invoices", cfg)

    assert decision["allowed"] is True
    assert decision["state"] == "half_open"


def test_half_open_failure_reopens_circuit() -> None:
    reset_circuit_breakers()
    cfg = {"circuit_breaker": {"enabled": True, "failure_threshold": 1, "recovery_seconds": 0}}
    record_circuit_failure("list_invoices", cfg)
    assert check_circuit_breaker("list_invoices", cfg)["state"] == "half_open"

    result = record_circuit_failure("list_invoices", cfg)

    assert result["state"] == "open"
    assert result["previous_state"] == "half_open"
