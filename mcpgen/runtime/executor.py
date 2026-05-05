import os
from time import perf_counter
from urllib.parse import urlencode

import httpx

from mcpgen.runtime.audit import build_audit_event, write_audit_event
from mcpgen.runtime.metrics import record_metric
from mcpgen.runtime.policy import evaluate_tool_policy

DEFAULT_TIMEOUT_SECONDS = 10.0


def execute_tool(tool_name: str, params: dict, config: dict, source: str = "fastapi") -> dict:
    """Execute only policy-approved low-risk GET tools."""
    tool = find_tool(tool_name, config.get("tools") or [])
    if tool is None:
        record_metric(
            {
                "action": "execution_error",
                "tool_name": tool_name,
                "status": "error",
                "allowed": False,
                "source": source,
                "latency_ms": 0.0,
            },
            config,
        )
        return execution_error(tool_name, "Tool not found.", source=source)

    policy_config = {**config, "source": source}
    policy = evaluate_tool_policy(tool, policy_config, mode=config.get("execution_mode", "dry-run"))
    if not is_executable_get(tool, policy):
        if policy.get("allowed"):
            policy = {
                "allowed": False,
                "status": "blocked",
                "reason": "Only low-risk GET tools can execute.",
                "risk_level": tool.get("risk_level", "unknown"),
                "tool_name": tool_name,
            }
        write_audit_event(
            build_audit_event(
                tool=tool,
                policy=policy,
                config=config,
                source=source,
                action="execution_blocked",
            )
        )
        record_execution_metric(tool, policy, config, source, "execution_blocked")
        return {
            "tool": tool_name,
            "status": "error",
            "status_code": None,
            "data": policy,
        }

    api_base_url = os.getenv("API_BASE_URL") or config.get("api_base_url")
    if not api_base_url:
        error = "Missing api_base_url config or API_BASE_URL environment variable."
        write_execution_event(tool, policy, config, source, "execution_error", reason=error, latency_ms=0.0)
        return {
            "tool": tool_name,
            "status": "error",
            "status_code": None,
            "data": {"error": error},
        }

    url = build_execution_url(api_base_url, tool, params)
    write_execution_event(tool, policy, config, source, "execution_started")
    started_at = perf_counter()

    try:
        response = httpx.get(url, timeout=DEFAULT_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = parse_response_data(response)
        write_execution_event(
            tool,
            policy,
            config,
            source,
            "execution_success",
            latency_ms=elapsed_ms(started_at),
        )
        return {
            "tool": tool_name,
            "status": "success",
            "status_code": response.status_code,
            "data": data,
        }
    except httpx.HTTPStatusError as exc:
        write_execution_event(
            tool,
            policy,
            config,
            source,
            "execution_error",
            reason=str(exc),
            latency_ms=elapsed_ms(started_at),
        )
        return {
            "tool": tool_name,
            "status": "error",
            "status_code": exc.response.status_code,
            "data": parse_response_data(exc.response),
        }
    except httpx.HTTPError as exc:
        write_execution_event(
            tool,
            policy,
            config,
            source,
            "execution_error",
            reason=str(exc),
            latency_ms=elapsed_ms(started_at),
        )
        return {
            "tool": tool_name,
            "status": "error",
            "status_code": None,
            "data": {"error": str(exc)},
        }


def find_tool(tool_name: str, tools: list[dict]) -> dict | None:
    for tool in tools:
        if tool.get("name") == tool_name:
            return tool
    return None


def is_executable_get(tool: dict, policy: dict) -> bool:
    return (
        policy.get("status") == "allowed"
        and policy.get("allowed") is True
        and tool.get("method", "").upper() == "GET"
        and tool.get("risk_level") == "low"
    )


def build_execution_url(api_base_url: str, tool: dict, params: dict) -> str:
    path = tool.get("path", "")
    query_params = {}

    for name, value in params.items():
        if input_location(tool, name) == "path":
            path = path.replace(f"{{{name}}}", str(value))
        else:
            query_params[name] = value

    base = api_base_url.rstrip("/")
    route = path if path.startswith("/") else f"/{path}"
    url = f"{base}{route}"
    if query_params:
        url = f"{url}?{urlencode(query_params)}"
    return url


def input_location(tool: dict, name: str) -> str:
    property_schema = tool.get("input_schema", {}).get("properties", {}).get(name, {})
    return property_schema.get("x-mcpgen-location", "query")


def parse_response_data(response: httpx.Response):
    try:
        return response.json()
    except ValueError:
        return response.text


def write_execution_event(
    tool: dict,
    policy: dict,
    config: dict,
    source: str,
    action: str,
    reason: str | None = None,
    latency_ms: float | None = None,
) -> None:
    event_policy = dict(policy)
    if reason is not None:
        event_policy["reason"] = reason
    write_audit_event(
        build_audit_event(
            tool=tool,
            policy=event_policy,
            config=config,
            source=source,
            action=action,
        )
    )
    record_execution_metric(tool, event_policy, config, source, action, latency_ms=latency_ms)


def record_execution_metric(
    tool: dict,
    policy: dict,
    config: dict,
    source: str,
    action: str,
    latency_ms: float | None = None,
) -> None:
    record_metric(
        {
            "action": action,
            "tool_name": policy.get("tool_name") or tool.get("name", "unknown"),
            "method": tool.get("method", "unknown"),
            "path": tool.get("path", "unknown"),
            "risk_level": policy.get("risk_level") or tool.get("risk_level", "unknown"),
            "status": policy.get("status", "unknown"),
            "allowed": policy.get("allowed", False),
            "source": source,
            "latency_ms": latency_ms,
        },
        config,
    )


def elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)


def execution_error(tool_name: str, message: str, source: str) -> dict:
    return {
        "tool": tool_name,
        "status": "error",
        "status_code": None,
        "data": {
            "error": message,
            "source": source,
        },
    }
