import json
from pathlib import Path
from typing import Any

from mcpgen.core.config import MCPGenConfig
from mcpgen.core.models import Tool, model_to_dict
from mcpgen.core.parser import parse_openapi
from mcpgen.core.routing_eval import evaluate_routing
from mcpgen.core.smoke import run_smoke_test
from mcpgen.core.tool_generator import generate_tools
from mcpgen.core.tool_selection import apply_tool_selection
from mcpgen.runtime.safety import filter_safe_tools


DEFAULT_BASELINE_PATH = Path("mcpgen.baseline.json")


def build_watchdog_baseline(spec_path: Path, config: MCPGenConfig) -> dict[str, Any]:
    """Build a deterministic baseline for spec/tool drift detection."""
    discovered_tools = generate_tools(parse_openapi(spec_path))
    selected_tools, selection_report = apply_tool_selection(discovered_tools, config)
    safe_tools = filter_safe_tools(selected_tools, allowed_methods=config.normalized_allowed_methods())
    safe_names = {tool.name for tool in safe_tools}

    return {
        "version": 1,
        "tool_counts": {
            "discovered": len(discovered_tools),
            "selected": len(selected_tools),
            "exposed": len(safe_tools),
            "excluded": len(selection_report["excluded"]),
            "withheld": len(selected_tools) - len(safe_tools),
        },
        "tools": [baseline_tool(tool, exposed=tool.name in safe_names) for tool in selected_tools],
    }


def baseline_tool(tool: Tool, exposed: bool) -> dict[str, Any]:
    return {
        "name": tool.name,
        "method": tool.method,
        "path": tool.path,
        "risk_level": tool.risk_level.value,
        "exposed": exposed,
        "input_schema": normalized_json(model_to_dict(tool, mode="json").get("input_schema") or {}),
        "response_schema": normalized_json(model_to_dict(tool, mode="json").get("response_schema")),
    }


def write_watchdog_baseline(baseline: dict[str, Any], path: Path = DEFAULT_BASELINE_PATH) -> None:
    path.write_text(json.dumps(baseline, indent=2, sort_keys=True), encoding="utf-8")


def load_watchdog_baseline(path: Path = DEFAULT_BASELINE_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_watchdog(
    spec_path: Path,
    config: MCPGenConfig,
    baseline_path: Path = DEFAULT_BASELINE_PATH,
    cases_path: Path | None = None,
    config_path: Path | None = None,
    mode: str = "fastapi",
    write_baseline: bool = False,
) -> dict[str, Any]:
    """Compare current spec/tool surface against a committed baseline."""
    current = build_watchdog_baseline(spec_path, config)
    checks = []

    if write_baseline:
        write_watchdog_baseline(current, baseline_path)
        return {
            "status": "pass",
            "baseline_written": True,
            "baseline_path": str(baseline_path),
            "checks": [pass_check("baseline", f"Wrote baseline to {baseline_path}.")],
            "current": current,
        }

    if not baseline_path.exists():
        return {
            "status": "fail",
            "baseline_written": False,
            "baseline_path": str(baseline_path),
            "checks": [fail_check("baseline", f"Baseline not found: {baseline_path}. Run with --write-baseline.")],
            "current": current,
        }

    previous = load_watchdog_baseline(baseline_path)
    checks.extend(compare_baselines(previous, current))

    smoke = run_smoke_test(spec_path, config, config_path=config_path, cases_path=cases_path, mode=mode)
    checks.append(check_from_status("smoke", smoke["status"], f"smoke completed with status {smoke['status']}"))

    if cases_path is not None:
        routing_eval = evaluate_routing(spec_path, cases_path, config=config)
        checks.append(
            check_from_status(
                "routing_eval",
                routing_eval["status"],
                f"{routing_eval['passed']}/{routing_eval['total']} routing case(s) passed.",
            )
        )

    status = "pass"
    if any(check["status"] == "fail" for check in checks):
        status = "fail"
    elif any(check["status"] == "warn" for check in checks):
        status = "warn"

    return {
        "status": status,
        "baseline_written": False,
        "baseline_path": str(baseline_path),
        "checks": checks,
        "current": current,
    }


def compare_baselines(previous: dict[str, Any], current: dict[str, Any]) -> list[dict]:
    checks = []
    previous_tools = {tool["name"]: tool for tool in previous.get("tools", [])}
    current_tools = {tool["name"]: tool for tool in current.get("tools", [])}

    removed = sorted(set(previous_tools) - set(current_tools))
    added = sorted(set(current_tools) - set(previous_tools))

    for name in removed:
        checks.append(fail_check("tool_removed", f"Removed tool: {name}."))
    for name in added:
        checks.append(warn_check("tool_added", f"New tool added: {name}."))

    for name in sorted(set(previous_tools) & set(current_tools)):
        checks.extend(compare_tool(previous_tools[name], current_tools[name]))

    if not checks:
        checks.append(pass_check("baseline", "No tool drift detected."))

    return checks


def compare_tool(previous: dict[str, Any], current: dict[str, Any]) -> list[dict]:
    checks = []
    name = current["name"]
    breaking_fields = ["method", "path", "risk_level", "input_schema", "response_schema", "exposed"]

    for field in breaking_fields:
        if previous.get(field) != current.get(field):
            checks.append(
                fail_check(
                    f"tool_{field}_changed",
                    f"{name} {field} changed.",
                    previous=previous.get(field),
                    current=current.get(field),
                )
            )

    return checks


def normalized_json(value) -> Any:
    if isinstance(value, dict):
        return {key: normalized_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [normalized_json(item) for item in value]
    return value


def check_from_status(name: str, status: str, message: str) -> dict:
    if status == "pass":
        return pass_check(name, message)
    if status == "warn":
        return warn_check(name, message)
    return fail_check(name, message)


def pass_check(name: str, message: str, **details) -> dict:
    return {"name": name, "status": "pass", "message": message, **details}


def warn_check(name: str, message: str, **details) -> dict:
    return {"name": name, "status": "warn", "message": message, **details}


def fail_check(name: str, message: str, **details) -> dict:
    return {"name": name, "status": "fail", "message": message, **details}
