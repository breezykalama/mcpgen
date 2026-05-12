import os
from time import perf_counter
from urllib.parse import urlencode

import httpx

from mcpgen.runtime.audit import build_audit_event, write_audit_event
from mcpgen.runtime.circuit_breaker import (
    check_circuit_breaker,
    record_circuit_failure,
    record_circuit_success,
)
from mcpgen.runtime.failure import build_failure_response, get_failure_scenario
from mcpgen.runtime.metrics import record_metric
from mcpgen.runtime.mock import build_mock_response, should_use_mock
from mcpgen.runtime.policy import evaluate_tool_policy
from mcpgen.runtime.retry import (
    max_attempts,
    retry_delay,
    should_retry_network_error,
    should_retry_status,
    sleep_before_retry,
)
from mcpgen.runtime.validation import validate_tool_inputs, validate_tool_response

DEFAULT_TIMEOUT_SECONDS = 10.0
SUPPORTED_AUTH_MODES = {"none", "bearer_passthrough", "api_key"}


def execute_tool(
    tool_name: str,
    params: dict,
    config: dict,
    source: str = "fastapi",
    incoming_headers: dict | None = None,
) -> dict:
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

    validation = validate_tool_inputs(tool, params)
    if not validation["valid"]:
        write_execution_event(tool, policy, config, source, "execution_error", reason="Input validation failed.", latency_ms=0.0)
        return {
            "tool": tool_name,
            "status": "error",
            "status_code": None,
            "data": validation,
        }

    circuit = check_circuit_breaker(tool_name, config)
    if not circuit["allowed"]:
        record_circuit_event(tool, config, source, "circuit_blocked", circuit)
        return {
            "tool": tool_name,
            "status": "error",
            "status_code": 503,
            "data": {
                "error": circuit["reason"],
                "state": circuit["state"],
                "retry_after": circuit["retry_after"],
                "do_not_retry_until": circuit.get("do_not_retry_until"),
                "agent_instruction": circuit.get("agent_instruction"),
            },
        }

    failure_scenario = get_failure_scenario(tool_name, config)
    if failure_scenario is not None:
        write_execution_event(tool, policy, config, source, "execution_started")
        result = build_failure_response(tool_name, failure_scenario)
        circuit_update = record_circuit_failure(tool_name, config)
        if circuit_update.get("state") == "open" and circuit_update.get("changed"):
            record_circuit_event(tool, config, source, "circuit_opened", circuit_update)
        write_execution_event(
            tool,
            policy,
            config,
            source,
            "execution_error",
            reason=f"Simulated failure: {failure_scenario}.",
            latency_ms=0.0,
        )
        return result

    if should_use_mock(config):
        write_execution_event(tool, policy, config, source, "execution_started")
        result = build_mock_response(tool, params, config)
        record_circuit_success(tool_name, config)
        write_execution_event(tool, policy, config, source, "execution_success", latency_ms=0.0)
        return result

    url = build_execution_url(api_base_url, tool, params)
    try:
        auth_headers = build_auth_headers(config, incoming_headers=incoming_headers)
    except ValueError as exc:
        write_execution_event(tool, policy, config, source, "execution_error", reason=str(exc), latency_ms=0.0)
        return {
            "tool": tool_name,
            "status": "error",
            "status_code": None,
            "data": {"error": str(exc)},
        }

    write_execution_event(tool, policy, config, source, "execution_started")
    started_at = perf_counter()

    attempt = 1

    while True:
        try:
            response = httpx.get(url, headers=auth_headers, timeout=DEFAULT_TIMEOUT_SECONDS)
            response.raise_for_status()
            data = parse_response_data(response)
            response_validation = validate_tool_response(tool, data)
            record_circuit_success(tool_name, config)
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
                "response_validation": response_validation,
            }
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if should_retry_status(status_code, attempt, config):
                write_retry_event(tool, policy, config, source, attempt, status_code, str(exc))
                sleep_before_retry(attempt, config)
                attempt += 1
                continue

            if status_code >= 500:
                circuit_update = record_circuit_failure(tool_name, config)
                if circuit_update.get("state") == "open" and circuit_update.get("changed"):
                    record_circuit_event(tool, config, source, "circuit_opened", circuit_update)
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
                "status_code": status_code,
                "data": parse_response_data(exc.response),
            }
        except httpx.HTTPError as exc:
            if should_retry_network_error(attempt, config):
                write_retry_event(tool, policy, config, source, attempt, None, str(exc))
                sleep_before_retry(attempt, config)
                attempt += 1
                continue

            circuit_update = record_circuit_failure(tool_name, config)
            if circuit_update.get("state") == "open" and circuit_update.get("changed"):
                record_circuit_event(tool, config, source, "circuit_opened", circuit_update)
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


def build_auth_headers(config: dict, incoming_headers: dict | None = None) -> dict:
    auth_config = config.get("auth") or {}
    mode = auth_config.get("mode", "none")

    if mode == "none":
        return {}

    if mode == "bearer_passthrough":
        authorization = find_header(incoming_headers or {}, "authorization")
        if authorization and authorization.startswith("Bearer "):
            return {"Authorization": authorization}
        return {}

    if mode == "api_key":
        env_name = auth_config.get("api_key_env") or "API_KEY"
        header_name = auth_config.get("api_key_header") or "X-API-Key"
        api_key = os.getenv(env_name)
        if not api_key:
            raise ValueError(f"Missing API key environment variable: {env_name}.")
        return {header_name: api_key}

    raise ValueError(f"Unsupported auth mode: {mode}.")


def find_header(headers: dict, name: str) -> str | None:
    for key, value in headers.items():
        if str(key).lower() == name.lower():
            return str(value)
    return None


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


def write_retry_event(
    tool: dict,
    policy: dict,
    config: dict,
    source: str,
    attempt: int,
    status_code: int | None,
    reason: str,
) -> None:
    event_policy = {
        **policy,
        "status": "retrying",
        "reason": reason,
        "attempt": attempt,
        "next_attempt": attempt + 1,
        "max_attempts": max_attempts(config),
        "retry_after": retry_delay(attempt, config),
    }
    if status_code is not None:
        event_policy["status_code"] = status_code
    event = build_audit_event(
        tool=tool,
        policy=event_policy,
        config=config,
        source=source,
        action="execution_retry",
    )
    event.update(
        {
            "attempt": event_policy["attempt"],
            "next_attempt": event_policy["next_attempt"],
            "max_attempts": event_policy["max_attempts"],
            "retry_after": event_policy["retry_after"],
        }
    )
    if status_code is not None:
        event["status_code"] = status_code
    write_audit_event(event)
    record_execution_metric(tool, event_policy, config, source, "execution_retry")


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


def record_circuit_event(tool: dict, config: dict, source: str, action: str, decision: dict) -> None:
    event = {
        "tool_name": tool.get("name", "unknown"),
        "method": tool.get("method", "unknown"),
        "path": tool.get("path", "unknown"),
        "risk_level": tool.get("risk_level", "unknown"),
        "mode": config.get("execution_mode", "dry-run"),
        "status": decision.get("state", "unknown"),
        "allowed": decision.get("allowed", False),
        "reason": decision.get("reason", "Circuit breaker event."),
        "source": source,
        "action": action,
        "retry_after": decision.get("retry_after", 0),
        "do_not_retry_until": decision.get("do_not_retry_until"),
        "agent_instruction": decision.get("agent_instruction"),
        "audit_enabled": config.get("audit_enabled", True),
        "audit_log_path": config.get("audit_log_path", "logs/audit.log"),
    }
    write_audit_event(event)
    record_metric(
        {
            "action": action,
            "tool_name": tool.get("name", "unknown"),
            "method": tool.get("method", "unknown"),
            "path": tool.get("path", "unknown"),
            "risk_level": tool.get("risk_level", "unknown"),
            "status": decision.get("state", "unknown"),
            "allowed": decision.get("allowed", False),
            "source": source,
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
