import json
import os
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

from mcpgen.runtime.registry import ToolRegistry
from mcpgen.runtime.audit import build_audit_event, write_audit_event
from mcpgen.runtime.dry_run import build_dry_run_request
from mcpgen.runtime.executor import execute_tool
from mcpgen.runtime.policy import evaluate_tool_policy
from mcpgen.runtime.router import rank_relevant_tools


class ToolQuery(BaseModel):
    query: str


class DryRunRequest(BaseModel):
    inputs: dict = Field(default_factory=dict)


class ExecuteRequest(BaseModel):
    tool_name: str
    params: dict = Field(default_factory=dict)


app = FastAPI(title="Generated MCPGen Server")
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
execution_config = dict(audit_config)
execution_config["tools"] = [tool.model_dump(mode="json") for tool in all_registry.list_tools()]


@app.get("/")
def root():
    return {
        "name": "MCPGen Generated Server",
        "mode": "fastapi",
        "status": "ok",
        "endpoints": {
            "health": "/health",
            "tools": "/tools",
            "route_tools": "POST /tools",
            "dry_run": "POST /tools/{tool_name}/dry-run",
            "execute": "POST /execute",
            "safety": "/safety",
            "docs": "/docs",
        },
    }


@app.post("/tools")
def list_relevant_tools(request: ToolQuery):
    ranked_tools = rank_relevant_tools(request.query, registry.list_tools(), limit=runtime_config.get("max_tools", 5))
    return {
        "tools": [
            {
                "tool": item["tool"].model_dump(mode="json"),
                "score": item["score"],
                "matched_terms": item["matched_terms"],
            }
            for item in ranked_tools
        ]
    }


@app.get("/tools")
def list_tools():
    return {"tools": [tool.model_dump(mode="json") for tool in registry.list_tools()]}


@app.post("/tools/{tool_name}/dry-run")
def dry_run_tool(tool_name: str, request: DryRunRequest):
    tool = all_registry.get_tool(tool_name)
    if tool is None:
        tool_data = {"name": tool_name, "method": "unknown", "path": "unknown", "risk_level": "unknown"}
        policy = evaluate_tool_policy(tool_data, runtime_config, mode=runtime_config.get("execution_mode", "dry-run"))
        write_audit_event(
            build_audit_event(
                tool=tool_data,
                policy=policy,
                config=audit_config,
                source="fastapi",
                action="policy_evaluation",
            )
        )
        return policy

    tool_data = tool.model_dump(mode="json")
    policy = evaluate_tool_policy(
        tool_data,
        runtime_config,
        mode=runtime_config.get("execution_mode", "dry-run"),
    )
    write_audit_event(
        build_audit_event(
            tool=tool_data,
            policy=policy,
            config=audit_config,
            source="fastapi",
            action="policy_evaluation",
        )
    )
    if not policy["allowed"]:
        return policy

    preview = build_dry_run_request(tool, request.inputs, api_base_url)
    write_audit_event(
        build_audit_event(
            tool=tool_data,
            policy=policy,
            config=audit_config,
            source="fastapi",
            action="dry_run",
        )
    )
    return preview


@app.post("/execute")
def execute(request: ExecuteRequest):
    return execute_tool(request.tool_name, request.params, execution_config, source="fastapi")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/safety")
def safety():
    return safety_report
