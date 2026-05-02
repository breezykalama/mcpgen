import json
import importlib.util
from pathlib import Path

from mcpgen.core.config import MCPGenConfig
from mcpgen.core.generator import generate_project


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
    assert len(embeddings) == 5
    assert embeddings[0]["tool_name"] == "list_customers"
    assert env_example == "API_BASE_URL=https://api.example.com\n"
    assert "mode: fastapi" in generated_config


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

    blocked = module.dry_run_tool(
        "create_invoice",
        module.DryRunRequest(inputs={"customerId": "cus_123", "amount": 50}),
    )
    assert blocked["status"] == "blocked"
    assert blocked["tool_name"] == "create_invoice"
    audit_events = [json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines()]
    assert audit_events[-1]["status"] == "blocked"

    def fake_execute_tool(tool_name, params, config, source="fastapi"):
        return {
            "tool": tool_name,
            "status": "success",
            "status_code": 200,
            "data": {"params": params, "source": source},
        }

    module.execute_tool = fake_execute_tool
    executed = module.execute(module.ExecuteRequest(tool_name="list_invoices", params={"customerId": "cus_123"}))
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


def test_mcp_safe_execute_calls_executor(tmp_path: Path) -> None:
    output_dir = tmp_path / "server"
    generate_project(Path("examples/openapi.yaml"), output_dir, config=MCPGenConfig(execution_mode="safe-execute"), mode="mcp")

    spec = importlib.util.spec_from_file_location("generated_test_mcp_execute_server", output_dir / "server.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def fake_execute_tool(tool_name, params, config, source="mcp"):
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
