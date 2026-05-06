import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from mcpgen.runtime.registry import ToolRegistry
from mcpgen.runtime.audit import build_audit_event, write_audit_event
from mcpgen.runtime.dry_run import build_dry_run_request
from mcpgen.runtime.executor import execute_tool
from mcpgen.runtime.metrics import read_metrics, record_metric, reset_metrics
from mcpgen.runtime.policy import evaluate_tool_policy
from mcpgen.runtime.rate_limit import check_rate_limit, record_rate_limit_hit
from mcpgen.runtime.router import rank_relevant_tools
from mcpgen.runtime.validation import validate_tool_inputs


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
tool_embeddings = json.loads((BASE_DIR / "tools.embeddings.json").read_text(encoding="utf-8"))
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
policy_config = {**metrics_config, "source": "fastapi"}
execution_config = dict(metrics_config)
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
            "metrics": "/metrics",
            "docs": "/docs",
        },
    }


@app.post("/tools")
def list_relevant_tools(request: ToolQuery):
    rate_limit = enforce_rate_limit(None)
    if rate_limit is not None:
        return rate_limit
    record_rate_limit_hit(None, runtime_config)
    ranked_tools = rank_relevant_tools(
        request.query,
        registry.list_tools(),
        limit=runtime_config.get("max_tools", 5),
        embeddings=tool_embeddings,
        routing_mode=runtime_config.get("routing_mode", "semantic"),
        config=metrics_config,
    )
    return {
        "tools": [
            {
                "tool": item["tool"].model_dump(mode="json"),
                "score": item["score"],
                "matched_terms": item["matched_terms"],
                "routing_mode": item.get("routing_mode", runtime_config.get("routing_mode", "semantic")),
            }
            for item in ranked_tools
        ]
    }


@app.get("/tools")
def list_tools():
    return {"tools": [tool.model_dump(mode="json") for tool in registry.list_tools()]}


@app.post("/tools/{tool_name}/dry-run")
def dry_run_tool(tool_name: str, request: DryRunRequest):
    rate_limit = enforce_rate_limit(tool_name)
    if rate_limit is not None:
        return rate_limit
    record_rate_limit_hit(tool_name, runtime_config)
    tool = all_registry.get_tool(tool_name)
    if tool is None:
        tool_data = {"name": tool_name, "method": "unknown", "path": "unknown", "risk_level": "unknown"}
        policy = evaluate_tool_policy(tool_data, policy_config, mode=runtime_config.get("execution_mode", "dry-run"))
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
        policy_config,
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

    validation = validate_tool_inputs(tool_data, request.inputs)
    if not validation["valid"]:
        return validation

    preview = build_dry_run_request(tool, request.inputs, api_base_url)
    record_metric(
        {
            "action": "dry_run",
            "tool_name": tool.name,
            "method": tool.method,
            "path": tool.path,
            "risk_level": tool.risk_level.value,
            "status": policy["status"],
            "allowed": policy["allowed"],
            "source": "fastapi",
        },
        metrics_config,
    )
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
def execute(payload: ExecuteRequest, request: Request):
    rate_limit = enforce_rate_limit(payload.tool_name)
    if rate_limit is not None:
        return rate_limit
    record_rate_limit_hit(payload.tool_name, runtime_config)
    return execute_tool(
        payload.tool_name,
        payload.params,
        execution_config,
        source="fastapi",
        incoming_headers=dict(request.headers),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/safety")
def safety():
    return safety_report


@app.get("/metrics")
def metrics():
    return read_metrics(metrics_config)


@app.post("/metrics/reset")
def reset_runtime_metrics():
    reset_metrics(metrics_config)
    return read_metrics(metrics_config)


def enforce_rate_limit(tool_name: str | None):
    decision = check_rate_limit(tool_name, runtime_config)
    if decision["allowed"]:
        return None

    tool = all_registry.get_tool(tool_name) if tool_name is not None else None
    tool_data = tool.model_dump(mode="json") if tool is not None else {
        "name": tool_name or "global",
        "method": "unknown",
        "path": "unknown",
        "risk_level": "unknown",
    }
    record_rate_limited(tool_data, decision, source="fastapi")
    body = rate_limited_body(decision)
    return JSONResponse(
        status_code=429,
        content=body,
        headers={"Retry-After": str(decision["retry_after"])},
    )


def rate_limited_body(decision: dict) -> dict:
    return {
        "status": "rate_limited",
        "scope": decision["scope"],
        "retry_after": decision["retry_after"],
        "reason": decision["reason"],
    }


def record_rate_limited(tool: dict, decision: dict, source: str) -> None:
    tool_name = tool.get("name", "unknown")
    record_metric(
        {
            "action": "rate_limited",
            "tool_name": tool_name,
            "scope": decision["scope"],
            "source": source,
        },
        metrics_config,
    )
    write_audit_event(
        {
            "tool_name": tool_name,
            "method": tool.get("method", "unknown"),
            "path": tool.get("path", "unknown"),
            "risk_level": tool.get("risk_level", "unknown"),
            "mode": runtime_config.get("execution_mode", "dry-run"),
            "status": "rate_limited",
            "allowed": False,
            "reason": decision["reason"],
            "source": source,
            "action": "rate_limited",
            "scope": decision["scope"],
            "retry_after": decision["retry_after"],
            "audit_enabled": audit_config.get("audit_enabled", True),
            "audit_log_path": audit_config.get("audit_log_path", "logs/audit.log"),
        }
    )
