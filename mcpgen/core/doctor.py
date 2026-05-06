from pathlib import Path

from pydantic import ValidationError

from mcpgen.core.config import MCPGenConfig, load_config
from mcpgen.core.inspector import inspect_spec
from mcpgen.core.parser import parse_openapi


VALID_AUTH_MODES = {"none", "bearer_passthrough", "api_key"}
VALID_EXECUTION_MODES = {"dry-run", "safe-execute"}
VALID_ROUTING_MODES = {"semantic", "keyword"}


def run_doctor(spec_path: Path, config_path: Path | None = None) -> dict:
    """Run read-only diagnostics for a spec/config pair."""
    checks = []
    config = None
    endpoints = []

    try:
        config = load_config(config_path)
        checks.append(pass_check("config", "Config loaded successfully."))
    except ValidationError as exc:
        checks.append(fail_check("config", f"Config validation failed: {exc.errors()[0]['msg']}"))
    except Exception as exc:
        checks.append(fail_check("config", f"Config could not be loaded: {exc}"))

    try:
        endpoints = parse_openapi(spec_path)
        checks.append(pass_check("openapi", f"Parsed {len(endpoints)} endpoint(s)."))
    except Exception as exc:
        checks.append(fail_check("openapi", f"OpenAPI spec could not be parsed: {exc}"))

    if config is not None:
        checks.extend(config_checks(config))

    if config is not None and endpoints:
        inspection = inspect_spec(spec_path, config=config)
        checks.extend(inspection_checks(inspection, config))

    status = "pass"
    if any(check["status"] == "fail" for check in checks):
        status = "fail"
    elif any(check["status"] == "warn" for check in checks):
        status = "warn"

    return {
        "status": status,
        "checks": checks,
    }


def config_checks(config: MCPGenConfig) -> list[dict]:
    checks = []

    if config.execution_mode in VALID_EXECUTION_MODES:
        checks.append(pass_check("execution_mode", f"execution_mode is {config.execution_mode}."))
    else:
        checks.append(fail_check("execution_mode", f"Invalid execution_mode: {config.execution_mode}."))

    if config.routing_mode in VALID_ROUTING_MODES:
        checks.append(pass_check("routing_mode", f"routing_mode is {config.routing_mode}."))
    else:
        checks.append(fail_check("routing_mode", f"Invalid routing_mode: {config.routing_mode}."))

    if config.api_base_url and config.api_base_url != "https://api.example.com":
        checks.append(pass_check("api_base_url", "api_base_url is configured."))
    else:
        checks.append(warn_check("api_base_url", "api_base_url is using the default placeholder."))

    auth_mode = config.auth.mode
    if auth_mode not in VALID_AUTH_MODES:
        checks.append(fail_check("auth", f"Invalid auth.mode: {auth_mode}."))
    elif auth_mode == "api_key" and not config.auth.api_key_env:
        checks.append(fail_check("auth", "auth.api_key_env is required when auth.mode is api_key."))
    elif auth_mode == "api_key" and not config.auth.api_key_header:
        checks.append(fail_check("auth", "auth.api_key_header is required when auth.mode is api_key."))
    else:
        checks.append(pass_check("auth", f"auth.mode is {auth_mode}."))

    rate_limit = config.rate_limit
    if rate_limit.enabled:
        if rate_limit.global_ <= 0 or rate_limit.per_tool <= 0 or rate_limit.window_seconds <= 0:
            checks.append(fail_check("rate_limit", "Enabled rate limits must be positive integers."))
        else:
            checks.append(pass_check("rate_limit", "Rate limiting is enabled and configured."))
    else:
        checks.append(warn_check("rate_limit", "Rate limiting is disabled."))

    if config.metrics_enabled:
        checks.append(pass_check("metrics", "Metrics are enabled."))
    else:
        checks.append(warn_check("metrics", "Metrics are disabled."))

    if config.audit_enabled:
        checks.append(pass_check("audit", "Audit logging is enabled."))
    else:
        checks.append(warn_check("audit", "Audit logging is disabled."))

    return checks


def inspection_checks(inspection: dict, config: MCPGenConfig) -> list[dict]:
    checks = []
    total_tools = inspection["total_tools"]
    exposed_tools = inspection["exposed_tools"]
    withheld_tools = inspection["withheld_tools"]

    if total_tools > 0:
        checks.append(pass_check("tools", f"Generated {total_tools} tool descriptor(s)."))
    else:
        checks.append(fail_check("tools", "No tools were generated from the spec."))

    if exposed_tools > 0:
        checks.append(pass_check("safety", f"{exposed_tools} low-risk tool(s) will be exposed."))
    else:
        checks.append(warn_check("safety", "No low-risk tools will be exposed."))

    if withheld_tools > 0:
        checks.append(pass_check("withheld_tools", f"{withheld_tools} risky tool(s) will be withheld."))
    else:
        checks.append(warn_check("withheld_tools", "No tools are withheld; confirm the spec has no write/delete operations."))

    if exposed_tools > config.max_tools:
        checks.append(
            warn_check(
                "tool_overload",
                f"{exposed_tools} tools are exposed, but max_tools is {config.max_tools}; routing will return a subset.",
            )
        )
    else:
        checks.append(pass_check("tool_overload", "Exposed tool count is within max_tools."))

    return checks


def pass_check(name: str, message: str) -> dict:
    return {"name": name, "status": "pass", "message": message}


def warn_check(name: str, message: str) -> dict:
    return {"name": name, "status": "warn", "message": message}


def fail_check(name: str, message: str) -> dict:
    return {"name": name, "status": "fail", "message": message}
