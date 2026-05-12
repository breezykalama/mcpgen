import json
from pathlib import Path

import httpx

from mcpgen.runtime.circuit_breaker import record_circuit_failure, reset_circuit_breakers
from mcpgen.runtime.executor import execute_tool
from mcpgen.runtime.metrics import read_metrics


def list_tool() -> dict:
    return {
        "name": "list_invoices",
        "description": "List invoices",
        "method": "GET",
        "path": "/invoices",
        "risk_level": "low",
        "input_schema": {"type": "object", "properties": {}},
    }


def config(tmp_path: Path, retry: dict | None = None) -> dict:
    return {
        "tools": [list_tool()],
        "api_base_url": "https://api.example.test",
        "execution_mode": "safe-execute",
        "audit_enabled": True,
        "audit_log_path": str(tmp_path / "logs" / "audit.log"),
        "metrics_enabled": True,
        "metrics_path": str(tmp_path / "logs" / "metrics.json"),
        "retry": retry or {"enabled": False},
    }


def test_retry_disabled_makes_one_attempt(monkeypatch, tmp_path: Path) -> None:
    calls = 0

    def fake_get(url, headers, timeout):
        nonlocal calls
        calls += 1
        return httpx.Response(500, json={"error": "bad"}, request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)

    result = execute_tool("list_invoices", {}, config(tmp_path))

    assert calls == 1
    assert result["status"] == "error"
    assert result["status_code"] == 500


def test_retry_http_status_then_success(monkeypatch, tmp_path: Path) -> None:
    calls = 0

    def fake_get(url, headers, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"error": "temporarily unavailable"}, request=httpx.Request("GET", url))
        return httpx.Response(200, json={"items": []}, request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    monkeypatch.setattr("mcpgen.runtime.retry.sleep", lambda seconds: None)
    cfg = config(tmp_path, {"enabled": True, "max_attempts": 3, "backoff_seconds": 0, "retry_statuses": [503]})

    result = execute_tool("list_invoices", {}, cfg)

    assert calls == 2
    assert result["status"] == "success"
    metrics = read_metrics(cfg)
    assert metrics["total_execution_retries"] == 1
    assert metrics["per_tool"]["list_invoices"]["retries"] == 1
    audit_text = (tmp_path / "logs" / "audit.log").read_text(encoding="utf-8")
    assert "execution_retry" in audit_text


def test_retry_exhaustion_returns_final_error(monkeypatch, tmp_path: Path) -> None:
    calls = 0

    def fake_get(url, headers, timeout):
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"error": "down"}, request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    monkeypatch.setattr("mcpgen.runtime.retry.sleep", lambda seconds: None)
    cfg = config(tmp_path, {"enabled": True, "max_attempts": 2, "backoff_seconds": 0, "retry_statuses": [503]})

    result = execute_tool("list_invoices", {}, cfg)

    assert calls == 2
    assert result["status"] == "error"
    assert result["status_code"] == 503
    metrics = read_metrics(cfg)
    assert metrics["total_execution_retries"] == 1
    assert metrics["total_execution_errors"] == 1


def test_retry_does_not_retry_non_retryable_status(monkeypatch, tmp_path: Path) -> None:
    calls = 0

    def fake_get(url, headers, timeout):
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "bad request"}, request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    cfg = config(tmp_path, {"enabled": True, "max_attempts": 3, "backoff_seconds": 0, "retry_statuses": [503]})

    result = execute_tool("list_invoices", {}, cfg)

    assert calls == 1
    assert result["status_code"] == 400


def test_retry_network_error_then_success(monkeypatch, tmp_path: Path) -> None:
    calls = 0

    def fake_get(url, headers, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("network unavailable", request=httpx.Request("GET", url))
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    monkeypatch.setattr("mcpgen.runtime.retry.sleep", lambda seconds: None)
    cfg = config(tmp_path, {"enabled": True, "max_attempts": 2, "backoff_seconds": 0})

    result = execute_tool("list_invoices", {}, cfg)

    assert calls == 2
    assert result["status"] == "success"
    assert read_metrics(cfg)["total_execution_retries"] == 1


def test_open_circuit_response_has_agent_retry_guidance(monkeypatch, tmp_path: Path) -> None:
    reset_circuit_breakers()
    called = False

    def fake_get(url, headers, timeout):
        nonlocal called
        called = True
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    cfg = {
        **config(tmp_path),
        "circuit_breaker": {"enabled": True, "failure_threshold": 1, "recovery_seconds": 60},
    }
    record_circuit_failure("list_invoices", cfg)

    result = execute_tool("list_invoices", {}, cfg)

    assert called is False
    assert result["status_code"] == 503
    assert result["data"]["retry_after"] >= 1
    assert result["data"]["do_not_retry_until"]
    assert "Do not retry this specific tool" in result["data"]["agent_instruction"]
    events = [
        json.loads(line)
        for line in (tmp_path / "logs" / "audit.log").read_text(encoding="utf-8").splitlines()
    ]
    assert events[0]["action"] == "circuit_blocked"
    assert events[0]["agent_instruction"].startswith("Do not retry")
