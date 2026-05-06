import json
import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from mcpgen.core.config import AuthConfig, MCPGenConfig, RateLimitConfig
from mcpgen.core.generator import generate_project
from mcpgen.runtime.rate_limit import reset_rate_limits


def test_generate_project_writes_only_safe_tools(tmp_path: Path) -> None:
    output_dir = tmp_path / "server"

    result = generate_project(Path("examples/openapi.yaml"), output_dir)
    tools = json.loads((output_dir / "tools.json").read_text(encoding="utf-8"))
    all_tools = json.loads((output_dir / "tools.all.json").read_text(encoding="utf-8"))
    safety_report = json.loads((output_dir / "safety_report.json").read_text(encoding="utf-8"))
    runtime_config = json.loads((output_dir / "mcpgen.runtime.json").read_text(encoding="utf-8"))
    embeddings = json.loads((output_dir / "tools.embeddings.json").read_text(encoding="utf-8"))
    env_example = (output_dir / ".env.example").read_text(encoding="utf-8")
    generated_config = (output_dir / "mcpgen.generated.yaml").read_text(encoding="utf-8")

    assert len(result.tools) == 2
    assert result.mode == "fastapi"
    assert len(result.all_tools) == 5
    assert (output_dir / "server.py").exists()
    assert [tool["name"] for tool in tools] == ["list_customers", "list_invoices"]
    assert [tool["name"] for tool in all_tools] == [
        "list_customers",
        "create_customer",
        "list_invoices",
        "create_invoice",
        "delete_invoice",
    ]
    assert all(tool["risk_level"] == "low" for tool in tools)
    assert safety_report["counts"] == {
        "total_tools": 5,
        "exposed_tools": 2,
        "withheld_tools": 3,
    }
    assert runtime_config["max_tools"] == 5
    assert runtime_config["mode"] == "fastapi"
    assert runtime_config["api_base_url"] == "https://api.example.com"
    assert runtime_config["enabled_tools"] == []
    assert runtime_config["execution_mode"] == "dry-run"
    assert runtime_config["audit_enabled"] is True
    assert runtime_config["audit_log_path"] == "logs/audit.log"
    assert runtime_config["routing_mode"] == "semantic"
    assert runtime_config["metrics_enabled"] is True
    assert runtime_config["metrics_path"] == "logs/metrics.json"
    assert runtime_config["auth"] == {
        "mode": "none",
        "api_key_env": "API_KEY",
        "api_key_header": "X-API-Key",
    }
    assert runtime_config["rate_limit"] == {
        "enabled": False,
        "per_tool": 10,
        "global": 100,
        "window_seconds": 60,
    }
    assert runtime_config["mock"] == {
        "enabled": False,
        "mode": "schema",
        "seed": 123,
        "list_size": 3,
    }
    assert runtime_config["failure_injection"] == {
        "enabled": False,
        "scenarios": {},
    }
    assert len(embeddings) == 5
    assert embeddings[0]["tool_name"] == "list_customers"
    assert env_example == "API_BASE_URL=https://api.example.com\n"
    assert "mode: fastapi" in generated_config
    assert "auth:" in generated_config
    assert "  mode: none" in generated_config
    assert "rate_limit:" in generated_config
    assert "  enabled: False" in generated_config
    assert "mock:" in generated_config
    assert "failure_injection:" in generated_config


def test_generate_project_honors_max_tools_config(tmp_path: Path) -> None:
    output_dir = tmp_path / "server"

    generate_project(Path("examples/openapi.yaml"), output_dir, config=MCPGenConfig(max_tools=1))
    runtime_config = json.loads((output_dir / "mcpgen.runtime.json").read_text(encoding="utf-8"))

    assert runtime_config["max_tools"] == 1


def test_generated_server_exposes_root_and_safety(tmp_path: Path) -> None:
    output_dir = tmp_path / "server"
    generate_project(Path("examples/openapi.yaml"), output_dir)

    spec = importlib.util.spec_from_file_location("generated_test_server", output_dir / "server.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.root()["endpoints"]["safety"] == "/safety"
    assert module.root()["endpoints"]["dry_run"] == "POST /tools/{tool_name}/dry-run"
    assert module.root()["endpoints"]["execute"] == "POST /execute"
    assert module.root()["endpoints"]["metrics"] == "/metrics"
    assert module.safety()["counts"]["withheld_tools"] == 3
    routed = module.list_relevant_tools(module.ToolQuery(query="invoice customer"))
    assert routed["tools"][0]["score"] >= 1
    assert "routing_mode" in routed["tools"][0]
    assert "tool" in routed["tools"][0]

    preview = module.dry_run_tool(
        "list_invoices",
        module.DryRunRequest(inputs={"customerId": "cus_123"}),
    )
    assert preview == {
        "tool": "list_invoices",
        "method": "GET",
        "url": "https://api.example.com/invoices?customerId=cus_123",
        "executed": False,
    }
    audit_log = output_dir / "logs" / "audit.log"
    audit_events = [json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines()]
    assert [event["action"] for event in audit_events[:2]] == ["policy_evaluation", "dry_run"]
    metrics = module.metrics()
    assert metrics["total_tool_routes"] >= 1
    assert metrics["total_policy_evaluations"] == 1
    assert metrics["total_dry_runs"] == 1
    assert metrics["per_tool"]["list_invoices"]["dry_runs"] == 1

    blocked = module.dry_run_tool(
        "create_invoice",
        module.DryRunRequest(inputs={"customerId": "cus_123", "amount": 50}),
    )
    assert blocked["status"] == "blocked"
    assert blocked["tool_name"] == "create_invoice"
    audit_events = [json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines()]
    assert audit_events[-1]["status"] == "blocked"
    metrics = module.metrics()
    assert metrics["per_tool"]["create_invoice"]["policy_blocked"] == 1

    def fake_execute_tool(tool_name, params, config, source="fastapi", incoming_headers=None):
        return {
            "tool": tool_name,
            "status": "success",
            "status_code": 200,
            "data": {"params": params, "source": source},
        }

    module.execute_tool = fake_execute_tool
    class FakeRequest:
        headers = {}

    executed = module.execute(
        module.ExecuteRequest(tool_name="list_invoices", params={"customerId": "cus_123"}),
        FakeRequest(),
    )
    assert executed == {
        "tool": "list_invoices",
        "status": "success",
        "status_code": 200,
        "data": {"params": {"customerId": "cus_123"}, "source": "fastapi"},
    }


def test_generate_project_supports_mcp_mode(tmp_path: Path) -> None:
    output_dir = tmp_path / "server"
    result = generate_project(Path("examples/openapi.yaml"), output_dir, mode="mcp")
    runtime_config = json.loads((output_dir / "mcpgen.runtime.json").read_text(encoding="utf-8"))

    spec = importlib.util.spec_from_file_location("generated_test_mcp_server", output_dir / "server.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert result.mode == "mcp"
    assert runtime_config["mode"] == "mcp"

    listed = module.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert listed["result"]["tools"][0]["name"] == "list_customers"
    assert [tool["name"] for tool in listed["result"]["tools"]] == ["list_customers", "list_invoices"]

    called = module.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "list_invoices",
                "arguments": {"customerId": "cus_123"},
            },
        }
    )
    assert called["result"]["isError"] is False
    assert '"executed": false' in called["result"]["content"][0]["text"]

    rejected = module.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "create_invoice",
                "arguments": {"customerId": "cus_123", "amount": 50},
            },
        }
    )
    assert rejected["result"]["isError"] is True
    assert "Medium-risk tool is not listed in enabled_tools" in rejected["result"]["content"][0]["text"]
    audit_log = output_dir / "logs" / "audit.log"
    audit_events = [json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines()]
    assert audit_events[0]["source"] == "mcp"
    assert audit_events[0]["action"] == "policy_evaluation"
    assert audit_events[1]["action"] == "dry_run"
    assert audit_events[-1]["status"] == "blocked"
    metrics = json.loads((output_dir / "logs" / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["total_policy_evaluations"] == 2
    assert metrics["total_dry_runs"] == 1


def test_mcp_safe_execute_calls_executor(tmp_path: Path) -> None:
    output_dir = tmp_path / "server"
    generate_project(Path("examples/openapi.yaml"), output_dir, config=MCPGenConfig(execution_mode="safe-execute"), mode="mcp")

    spec = importlib.util.spec_from_file_location("generated_test_mcp_execute_server", output_dir / "server.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def fake_execute_tool(tool_name, params, config, source="mcp", incoming_headers=None):
        return {
            "tool": tool_name,
            "status": "success",
            "status_code": 200,
            "data": {"params": params, "source": source},
        }

    module.execute_tool = fake_execute_tool
    result = module.call_mcp_tool("list_invoices", {"customerId": "cus_123"})

    assert result["isError"] is False
    assert '"status": "success"' in result["content"][0]["text"]
    assert '"source": "mcp"' in result["content"][0]["text"]


def test_mcp_api_key_mode_calls_executor(tmp_path: Path) -> None:
    output_dir = tmp_path / "server"
    generate_project(
        Path("examples/openapi.yaml"),
        output_dir,
        config=MCPGenConfig(execution_mode="safe-execute", auth=AuthConfig(mode="api_key")),
        mode="mcp",
    )

    spec = importlib.util.spec_from_file_location("generated_test_mcp_api_key_server", output_dir / "server.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def fake_execute_tool(tool_name, params, config, source="mcp", incoming_headers=None):
        return {
            "tool": tool_name,
            "status": "success",
            "status_code": 200,
            "data": {"auth_mode": config["auth"]["mode"], "incoming_headers": incoming_headers},
        }

    module.execute_tool = fake_execute_tool
    result = module.call_mcp_tool("list_invoices", {"customerId": "cus_123"})

    assert result["isError"] is False
    assert '"auth_mode": "api_key"' in result["content"][0]["text"]
    assert '"incoming_headers": {}' in result["content"][0]["text"]


def test_mcp_bearer_passthrough_requires_or_uses_auth_metadata(tmp_path: Path) -> None:
    output_dir = tmp_path / "server"
    generate_project(
        Path("examples/openapi.yaml"),
        output_dir,
        config=MCPGenConfig(execution_mode="safe-execute", auth=AuthConfig(mode="bearer_passthrough")),
        mode="mcp",
    )

    spec = importlib.util.spec_from_file_location("generated_test_mcp_bearer_server", output_dir / "server.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    captured = {}

    def fake_execute_tool(tool_name, params, config, source="mcp", incoming_headers=None):
        captured["params"] = params
        captured["incoming_headers"] = incoming_headers
        return {
            "tool": tool_name,
            "status": "success",
            "status_code": 200,
            "data": {"ok": True},
        }

    module.execute_tool = fake_execute_tool
    missing = module.call_mcp_tool("list_invoices", {"customerId": "cus_123"})
    assert missing["isError"] is True
    assert "requires auth.authorization metadata" in missing["content"][0]["text"]

    result = module.call_mcp_tool(
        "list_invoices",
        {
            "customerId": "cus_123",
            "auth": {"authorization": "Bearer mcp-token"},
        },
    )

    assert result["isError"] is False
    assert captured["params"] == {"customerId": "cus_123"}
    assert captured["incoming_headers"] == {"Authorization": "Bearer mcp-token"}


def test_fastapi_global_rate_limit_returns_429(tmp_path: Path) -> None:
    reset_rate_limits()
    output_dir = tmp_path / "server"
    generate_project(
        Path("examples/openapi.yaml"),
        output_dir,
        config=MCPGenConfig(rate_limit=RateLimitConfig(enabled=True, global_=1, per_tool=10, window_seconds=60)),
    )
    module = load_generated_module(output_dir / "server.py", "generated_test_global_rate_limit")
    client = TestClient(module.app)

    first = client.post("/tools", json={"query": "invoice"})
    second = client.post("/tools", json={"query": "invoice"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["retry-after"]
    assert second.json()["status"] == "rate_limited"
    assert second.json()["scope"] == "global"
    metrics = module.metrics()
    assert metrics["total_rate_limited"] == 1
    audit_events = read_audit_events(output_dir)
    assert audit_events[-1]["action"] == "rate_limited"


def test_generated_fastapi_dry_run_validates_inputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "server"
    generate_project(Path("examples/jsonplaceholder.openapi.yaml"), output_dir)
    module = load_generated_module(output_dir / "server.py", "generated_test_fastapi_validation")

    missing = module.dry_run_tool("get_user_by_id", module.DryRunRequest(inputs={}))
    wrong_type = module.dry_run_tool("get_user_by_id", module.DryRunRequest(inputs={"id": "1"}))

    assert missing["status"] == "validation_error"
    assert missing["errors"][0]["field"] == "id"
    assert wrong_type["status"] == "validation_error"
    assert wrong_type["errors"][0]["reason"] == "expected integer"


def test_fastapi_per_tool_rate_limit_returns_429(tmp_path: Path) -> None:
    reset_rate_limits()
    output_dir = tmp_path / "server"
    generate_project(
        Path("examples/openapi.yaml"),
        output_dir,
        config=MCPGenConfig(rate_limit=RateLimitConfig(enabled=True, global_=100, per_tool=1, window_seconds=60)),
    )
    module = load_generated_module(output_dir / "server.py", "generated_test_tool_rate_limit")
    client = TestClient(module.app)

    first = client.post("/tools/list_invoices/dry-run", json={"inputs": {}})
    second = client.post("/tools/list_invoices/dry-run", json={"inputs": {}})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["retry-after"]
    assert second.json()["scope"] == "per_tool"
    metrics = module.metrics()
    assert metrics["total_rate_limited"] == 1
    assert metrics["per_tool"]["list_invoices"]["rate_limited"] == 1


def test_rate_limit_disabled_allows_requests_and_health_is_not_limited(tmp_path: Path) -> None:
    reset_rate_limits()
    output_dir = tmp_path / "server"
    generate_project(Path("examples/openapi.yaml"), output_dir)
    module = load_generated_module(output_dir / "server.py", "generated_test_rate_limit_disabled")
    client = TestClient(module.app)

    for _ in range(3):
        assert client.post("/tools/list_invoices/dry-run", json={"inputs": {}}).status_code == 200
        assert client.get("/health").status_code == 200


def test_mcp_tools_call_rate_limit_works(tmp_path: Path) -> None:
    reset_rate_limits()
    output_dir = tmp_path / "server"
    generate_project(
        Path("examples/openapi.yaml"),
        output_dir,
        config=MCPGenConfig(rate_limit=RateLimitConfig(enabled=True, global_=100, per_tool=1, window_seconds=60)),
        mode="mcp",
    )
    module = load_generated_module(output_dir / "server.py", "generated_test_mcp_rate_limit")

    first = module.call_mcp_tool("list_invoices", {})
    second = module.call_mcp_tool("list_invoices", {})

    assert first["isError"] is False
    assert second["isError"] is True
    assert '"status": "rate_limited"' in second["content"][0]["text"]
    metrics = json.loads((output_dir / "logs" / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["total_rate_limited"] == 1
    assert metrics["per_tool"]["list_invoices"]["rate_limited"] == 1


def test_generated_mcp_tools_call_validates_inputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "server"
    generate_project(Path("examples/jsonplaceholder.openapi.yaml"), output_dir, mode="mcp")
    module = load_generated_module(output_dir / "server.py", "generated_test_mcp_validation")

    result = module.call_mcp_tool("get_user_by_id", {})

    assert result["isError"] is True
    assert '"status": "validation_error"' in result["content"][0]["text"]
    assert '"field": "id"' in result["content"][0]["text"]


def load_generated_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_audit_events(output_dir: Path) -> list[dict]:
    audit_log = output_dir / "logs" / "audit.log"
    return [json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines()]
