import json
import os
import sys
from pathlib import Path

from mcpgen.runtime.audit import build_audit_event, write_audit_event
from mcpgen.runtime.dry_run import build_dry_run_request
from mcpgen.runtime.executor import execute_tool
from mcpgen.runtime.metrics import record_metric
from mcpgen.runtime.policy import evaluate_tool_policy
from mcpgen.runtime.registry import ToolRegistry


try:
    import mcp  # noqa: F401

    MCP_SDK_AVAILABLE = True
except ImportError:
    MCP_SDK_AVAILABLE = False


BASE_DIR = Path(__file__).parent
registry = ToolRegistry.from_json(BASE_DIR / "tools.json")
all_registry = ToolRegistry.from_json(BASE_DIR / "tools.all.json")
runtime_config = json.loads((BASE_DIR / "mcpgen.runtime.json").read_text(encoding="utf-8"))
safety_report = json.loads((BASE_DIR / "safety_report.json").read_text(encoding="utf-8"))
api_base_url = os.getenv("API_BASE_URL", runtime_config.get("api_base_url", "https://api.example.com"))
audit_config = dict(runtime_config)
audit_log_path = Path(audit_config.get("audit_log_path", "logs/audit.log"))
if not audit_log_path.is_absolute():
    audit_config["audit_log_path"] = str(BASE_DIR / audit_log_path)
metrics_config = dict(audit_config)
metrics_path = Path(metrics_config.get("metrics_path", "logs/metrics.json"))
if not metrics_path.is_absolute():
    metrics_config["metrics_path"] = str(BASE_DIR / metrics_path)
policy_config = {**metrics_config, "source": "mcp"}
execution_config = dict(metrics_config)
execution_config["tools"] = [tool.model_dump(mode="json") for tool in all_registry.list_tools()]


def list_mcp_tools() -> list[dict]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.input_schema or {"type": "object", "properties": {}},
        }
        for tool in registry.list_tools()
    ]


def call_mcp_tool(name: str, arguments: dict | None = None) -> dict:
    tool = all_registry.get_tool(name)
    if tool is None:
        tool_data = {"name": name, "method": "unknown", "path": "unknown", "risk_level": "unknown"}
        policy = evaluate_tool_policy(
            tool_data,
            policy_config,
            mode=runtime_config.get("execution_mode", "dry-run"),
        )
        write_audit_event(
            build_audit_event(
                tool=tool_data,
                policy=policy,
                config=audit_config,
                source="mcp",
                action="policy_evaluation",
            )
        )
        return mcp_policy_result(policy)

    tool_data = tool.model_dump(mode="json")
    policy = evaluate_tool_policy(
        tool_data,
        policy_config,
        mode=runtime_config.get("execution_mode", "dry-run"),
    )
    write_audit_event(
        build_audit_event(
            tool=tool_data,
            policy=policy,
            config=audit_config,
            source="mcp",
            action="policy_evaluation",
        )
    )
    if not policy["allowed"]:
        return mcp_policy_result(policy)

    if runtime_config.get("execution_mode") == "safe-execute":
        result = execute_tool(name, arguments or {}, execution_config, source="mcp")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2),
                }
            ],
            "isError": result.get("status") == "error",
        }

    preview = build_dry_run_request(tool, arguments or {}, api_base_url)
    record_metric(
        {
            "action": "dry_run",
            "tool_name": tool.name,
            "method": tool.method,
            "path": tool.path,
            "risk_level": tool.risk_level.value,
            "status": policy["status"],
            "allowed": policy["allowed"],
            "source": "mcp",
        },
        metrics_config,
    )
    write_audit_event(
        build_audit_event(
            tool=tool_data,
            policy=policy,
            config=audit_config,
            source="mcp",
            action="dry_run",
        )
    )
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(preview, indent=2),
            }
        ],
        "isError": False,
    }


def mcp_policy_result(policy: dict) -> dict:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(policy, indent=2),
            }
        ],
        "isError": True,
    }


def handle_request(request: dict) -> dict | None:
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params") or {}

    if method == "notifications/initialized":
        return None

    try:
        if method == "initialize":
            result = {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "serverInfo": {
                    "name": "MCPGen Generated Server",
                    "version": "0.1.0",
                },
                "capabilities": {
                    "tools": {},
                    "experimental": {
                        "mcpgenFallbackStdio": not MCP_SDK_AVAILABLE,
                    },
                },
            }
        elif method == "tools/list":
            result = {"tools": list_mcp_tools()}
        elif method == "tools/call":
            result = call_mcp_tool(params.get("name", ""), params.get("arguments") or {})
        elif method == "mcpgen/safety":
            result = safety_report
        else:
            return error_response(request_id, -32601, f"Method not found: {method}")

        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except ValueError as exc:
        return error_response(request_id, -32602, str(exc))
    except Exception as exc:
        return error_response(request_id, -32603, str(exc))


def error_response(request_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def run_stdio() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue

        response = handle_request(json.loads(line))
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio()
