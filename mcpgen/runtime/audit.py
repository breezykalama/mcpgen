import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_AUDIT_LOG_PATH = "logs/audit.log"
INTERNAL_KEYS = {"audit_enabled", "audit_log_path"}


def write_audit_event(event: dict) -> None:
    """Write one audit event as JSONL when auditing is enabled."""
    if event.get("audit_enabled", True) is False:
        return

    log_path = Path(event.get("audit_log_path") or DEFAULT_AUDIT_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    record = {key: value for key, value in event.items() if key not in INTERNAL_KEYS}
    record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    with log_path.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(record, sort_keys=True) + "\n")


def build_audit_event(
    *,
    tool: dict,
    policy: dict,
    config: dict,
    source: str,
    action: str,
) -> dict:
    return {
        "tool_name": policy.get("tool_name") or tool.get("name") or "unknown",
        "method": tool.get("method", "unknown"),
        "path": tool.get("path", "unknown"),
        "risk_level": policy.get("risk_level") or tool.get("risk_level", "unknown"),
        "mode": config.get("execution_mode", "dry-run"),
        "status": policy.get("status", "unknown"),
        "allowed": policy.get("allowed", False),
        "reason": policy.get("reason", ""),
        "source": source,
        "action": action,
        "audit_enabled": config.get("audit_enabled", True),
        "audit_log_path": config.get("audit_log_path", DEFAULT_AUDIT_LOG_PATH),
    }
