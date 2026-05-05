import json
from datetime import datetime, timezone
from pathlib import Path

from mcpgen.runtime.audit import sanitize_event


DEFAULT_METRICS_PATH = "logs/metrics.json"
INTERNAL_KEYS = {"metrics_enabled", "metrics_path"}


def record_metric(event: dict, config: dict) -> None:
    """Update aggregate runtime metrics when metrics are enabled."""
    if config.get("metrics_enabled") is not True:
        return

    metrics_path = Path(config.get("metrics_path") or DEFAULT_METRICS_PATH)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    metrics = _load_metrics(metrics_path)
    _apply_event(metrics, sanitize_event(event))
    metrics["last_updated"] = datetime.now(timezone.utc).isoformat()
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")


def read_metrics(config: dict) -> dict:
    """Read the current metrics summary."""
    metrics_path = Path(config.get("metrics_path") or DEFAULT_METRICS_PATH)
    if not metrics_path.exists():
        return _empty_metrics()
    return _load_metrics(metrics_path)


def reset_metrics(config: dict) -> None:
    """Reset metrics back to an empty aggregate."""
    if config.get("metrics_enabled") is not True:
        return

    metrics_path = Path(config.get("metrics_path") or DEFAULT_METRICS_PATH)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics = _empty_metrics()
    metrics["last_updated"] = datetime.now(timezone.utc).isoformat()
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")


def _load_metrics(path: Path) -> dict:
    if not path.exists():
        return _empty_metrics()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _empty_metrics()

    metrics = _empty_metrics()
    metrics.update(data)
    metrics.setdefault("per_tool", {})
    return metrics


def _empty_metrics() -> dict:
    return {
        "total_tool_routes": 0,
        "total_policy_evaluations": 0,
        "total_executions": 0,
        "total_execution_success": 0,
        "total_execution_errors": 0,
        "total_execution_blocked": 0,
        "total_dry_runs": 0,
        "total_confirmation_required": 0,
        "total_rate_limited": 0,
        "per_tool": {},
        "last_updated": None,
    }


def _empty_tool_metrics() -> dict:
    return {
        "routed": 0,
        "policy_allowed": 0,
        "policy_blocked": 0,
        "dry_runs": 0,
        "executions": 0,
        "successes": 0,
        "errors": 0,
        "blocked": 0,
        "rate_limited": 0,
        "average_execution_latency_ms": 0.0,
        "execution_latency_total_ms": 0.0,
        "execution_latency_count": 0,
    }


def _tool_metrics(metrics: dict, tool_name: str) -> dict:
    per_tool = metrics.setdefault("per_tool", {})
    if tool_name not in per_tool:
        per_tool[tool_name] = _empty_tool_metrics()
    return per_tool[tool_name]


def _apply_event(metrics: dict, event: dict) -> None:
    action = event.get("action")
    tool_name = event.get("tool_name") or event.get("name") or "unknown"
    tool_metrics = _tool_metrics(metrics, tool_name)

    if action == "tool_routed":
        metrics["total_tool_routes"] += 1
        tool_metrics["routed"] += 1
        if event.get("routing_mode"):
            tool_metrics["last_routing_mode"] = event["routing_mode"]
        return

    if action == "policy_evaluation":
        metrics["total_policy_evaluations"] += 1
        status = event.get("status")
        if status == "allowed":
            tool_metrics["policy_allowed"] += 1
        elif status == "confirmation_required":
            metrics["total_confirmation_required"] += 1
            tool_metrics["policy_blocked"] += 1
        else:
            tool_metrics["policy_blocked"] += 1
        return

    if action == "dry_run":
        metrics["total_dry_runs"] += 1
        tool_metrics["dry_runs"] += 1
        return

    if action == "execution_started":
        metrics["total_executions"] += 1
        tool_metrics["executions"] += 1
        return

    if action == "execution_success":
        metrics["total_execution_success"] += 1
        tool_metrics["successes"] += 1
        _record_latency(tool_metrics, event.get("latency_ms"))
        return

    if action == "execution_error":
        metrics["total_execution_errors"] += 1
        tool_metrics["errors"] += 1
        _record_latency(tool_metrics, event.get("latency_ms"))
        return

    if action == "execution_blocked":
        metrics["total_execution_blocked"] += 1
        tool_metrics["blocked"] += 1
        return

    if action == "rate_limited":
        metrics["total_rate_limited"] += 1
        tool_metrics["rate_limited"] += 1


def _record_latency(tool_metrics: dict, latency_ms) -> None:
    if latency_ms is None:
        return

    latency = float(latency_ms)
    tool_metrics["execution_latency_total_ms"] += latency
    tool_metrics["execution_latency_count"] += 1
    count = tool_metrics["execution_latency_count"]
    tool_metrics["average_execution_latency_ms"] = round(
        tool_metrics["execution_latency_total_ms"] / count,
        3,
    )
