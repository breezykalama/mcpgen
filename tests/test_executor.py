import json
from pathlib import Path

import httpx

from mcpgen.runtime.executor import build_auth_headers, build_execution_url, execute_tool


def make_config(tmp_path: Path, tools: list[dict], api_base_url: str = "https://api.example.test") -> dict:
    return {
        "tools": tools,
        "api_base_url": api_base_url,
        "execution_mode": "safe-execute",
        "enabled_tools": [],
        "audit_log_path": str(tmp_path / "logs" / "audit.log"),
    }


def list_invoice_tool() -> dict:
    return {
        "name": "list_invoices",
        "description": "List invoices",
        "method": "GET",
        "path": "/invoices",
        "risk_level": "low",
        "input_schema": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "x-mcpgen-location": "query"},
            },
        },
    }


def get_user_tool() -> dict:
    return {
        "name": "get_user_by_id",
        "description": "Get user by ID",
        "method": "GET",
        "path": "/users/{id}",
        "risk_level": "low",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "x-mcpgen-location": "path"},
                "include": {"type": "string", "x-mcpgen-location": "query"},
            },
            "required": ["id"],
        },
    }


def test_get_execution_success(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return httpx.Response(200, json={"items": []}, request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    config = make_config(tmp_path, [list_invoice_tool()])

    result = execute_tool("list_invoices", {"customerId": "cus_123"}, config)

    assert result == {
        "tool": "list_invoices",
        "status": "success",
        "status_code": 200,
        "data": {"items": []},
    }
    assert captured["url"] == "https://api.example.test/invoices?customerId=cus_123"
    assert captured["headers"] == {}
    assert captured["timeout"] == 10.0


def test_path_param_replacement_and_query_params() -> None:
    url = build_execution_url(
        "https://api.example.test",
        get_user_tool(),
        {"id": 1, "include": "profile"},
    )

    assert url == "https://api.example.test/users/1?include=profile"


def test_missing_api_base_url_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("API_BASE_URL", raising=False)
    config = make_config(tmp_path, [list_invoice_tool()], api_base_url="")

    result = execute_tool("list_invoices", {}, config)

    assert result["status"] == "error"
    assert result["status_code"] is None
    assert result["data"]["error"] == "Missing api_base_url config or API_BASE_URL environment variable."


def test_medium_risk_blocked(tmp_path: Path) -> None:
    tool = {
        "name": "create_invoice",
        "description": "Create invoice",
        "method": "POST",
        "path": "/invoices",
        "risk_level": "medium",
        "input_schema": {"type": "object", "properties": {}},
    }
    config = make_config(tmp_path, [tool])

    result = execute_tool("create_invoice", {"amount": 50}, config)

    assert result["status"] == "error"
    assert result["data"]["status"] == "blocked"
    assert result["data"]["reason"] == "Medium-risk tool is not listed in enabled_tools."
    events = [
        json.loads(line)
        for line in (tmp_path / "logs" / "audit.log").read_text(encoding="utf-8").splitlines()
    ]
    assert events[0]["action"] == "execution_blocked"
    assert events[0]["status"] == "blocked"


def test_high_risk_blocked(tmp_path: Path) -> None:
    tool = {
        "name": "delete_invoice",
        "description": "Delete invoice",
        "method": "DELETE",
        "path": "/invoices/{id}",
        "risk_level": "high",
        "input_schema": {"type": "object", "properties": {}},
    }
    config = make_config(tmp_path, [tool])

    result = execute_tool("delete_invoice", {"id": 1}, config)

    assert result["status"] == "error"
    assert result["data"]["status"] == "blocked"
    assert result["data"]["reason"] == "High-risk tools are always blocked."


def test_audit_events_written(monkeypatch, tmp_path: Path) -> None:
    def fake_get(url, headers, timeout):
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    config = make_config(tmp_path, [list_invoice_tool()])

    execute_tool("list_invoices", {}, config, source="fastapi")
    execute_tool(
        "missing_tool",
        {},
        {
            **config,
            "tools": [],
        },
        source="fastapi",
    )

    events = [
        json.loads(line)
        for line in (tmp_path / "logs" / "audit.log").read_text(encoding="utf-8").splitlines()
    ]

    assert [event["action"] for event in events[:2]] == ["execution_started", "execution_success"]


def test_bearer_passthrough_forwards_valid_bearer_token(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_get(url, headers, timeout):
        captured["headers"] = headers
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    config = {
        **make_config(tmp_path, [list_invoice_tool()]),
        "auth": {"mode": "bearer_passthrough"},
    }

    execute_tool(
        "list_invoices",
        {},
        config,
        incoming_headers={"Authorization": "Bearer test-token"},
    )

    assert captured["headers"] == {"Authorization": "Bearer test-token"}


def test_bearer_passthrough_ignores_non_bearer_authorization(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_get(url, headers, timeout):
        captured["headers"] = headers
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    config = {
        **make_config(tmp_path, [list_invoice_tool()]),
        "auth": {"mode": "bearer_passthrough"},
    }

    execute_tool(
        "list_invoices",
        {},
        config,
        incoming_headers={"Authorization": "Basic nope"},
    )

    assert captured["headers"] == {}


def test_api_key_injects_configured_header(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_get(url, headers, timeout):
        captured["headers"] = headers
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setenv("BILLING_API_KEY", "secret-key")
    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    config = {
        **make_config(tmp_path, [list_invoice_tool()]),
        "auth": {
            "mode": "api_key",
            "api_key_env": "BILLING_API_KEY",
            "api_key_header": "X-Billing-Key",
        },
    }

    execute_tool("list_invoices", {}, config)

    assert captured["headers"] == {"X-Billing-Key": "secret-key"}


def test_auth_headers_are_not_written_to_audit_or_metrics(monkeypatch, tmp_path: Path) -> None:
    def fake_get(url, headers, timeout):
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setenv("BILLING_API_KEY", "super-secret")
    monkeypatch.setattr("mcpgen.runtime.executor.httpx.get", fake_get)
    config = {
        **make_config(tmp_path, [list_invoice_tool()]),
        "auth": {
            "mode": "api_key",
            "api_key_env": "BILLING_API_KEY",
            "api_key_header": "X-Billing-Key",
        },
        "metrics_enabled": True,
        "metrics_path": str(tmp_path / "logs" / "metrics.json"),
    }

    execute_tool("list_invoices", {}, config)

    audit_text = (tmp_path / "logs" / "audit.log").read_text(encoding="utf-8")
    metrics_text = (tmp_path / "logs" / "metrics.json").read_text(encoding="utf-8")
    combined = f"{audit_text}\n{metrics_text}"
    assert "super-secret" not in combined
    assert "X-Billing-Key" not in combined
    assert "BILLING_API_KEY" not in combined


def test_missing_api_key_env_returns_clear_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("BILLING_API_KEY", raising=False)
    config = {
        **make_config(tmp_path, [list_invoice_tool()]),
        "auth": {
            "mode": "api_key",
            "api_key_env": "BILLING_API_KEY",
            "api_key_header": "X-Billing-Key",
        },
    }

    result = execute_tool("list_invoices", {}, config)

    assert result["status"] == "error"
    assert result["data"]["error"] == "Missing API key environment variable: BILLING_API_KEY."


def test_unknown_auth_mode_blocks_safely(tmp_path: Path) -> None:
    config = {
        **make_config(tmp_path, [list_invoice_tool()]),
        "auth": {"mode": "oauth2"},
    }

    result = execute_tool("list_invoices", {}, config)

    assert result["status"] == "error"
    assert result["data"]["error"] == "Unsupported auth mode: oauth2."


def test_build_auth_headers_case_insensitive_authorization() -> None:
    headers = build_auth_headers(
        {"auth": {"mode": "bearer_passthrough"}},
        incoming_headers={"authorization": "Bearer token"},
    )

    assert headers == {"Authorization": "Bearer token"}
