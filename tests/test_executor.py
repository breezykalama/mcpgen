import json
from pathlib import Path

import httpx

from mcpgen.runtime.executor import build_execution_url, execute_tool


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

    def fake_get(url, timeout):
        captured["url"] = url
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
    def fake_get(url, timeout):
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
