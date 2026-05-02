import json
from pathlib import Path

from mcpgen.runtime.audit import build_audit_event, write_audit_event
from mcpgen.runtime.policy import evaluate_tool_policy


def read_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_audit_event_is_written(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "audit.log"

    write_audit_event(
        {
            "tool_name": "list_invoices",
            "method": "GET",
            "path": "/invoices",
            "risk_level": "low",
            "mode": "dry-run",
            "status": "allowed",
            "allowed": True,
            "reason": "Low-risk GET tool is allowed.",
            "source": "fastapi",
            "action": "dry_run",
            "audit_log_path": str(log_path),
        }
    )

    events = read_events(log_path)

    assert len(events) == 1
    assert events[0]["timestamp"]
    assert events[0]["tool_name"] == "list_invoices"
    assert events[0]["action"] == "dry_run"


def test_audit_disabled_writes_nothing(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "audit.log"

    write_audit_event(
        {
            "tool_name": "list_invoices",
            "method": "GET",
            "path": "/invoices",
            "risk_level": "low",
            "mode": "dry-run",
            "status": "allowed",
            "allowed": True,
            "reason": "Low-risk GET tool is allowed.",
            "source": "fastapi",
            "action": "dry_run",
            "audit_enabled": False,
            "audit_log_path": str(log_path),
        }
    )

    assert not log_path.exists()


def test_blocked_tool_attempt_is_logged(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "audit.log"
    tool = {
        "name": "create_invoice",
        "method": "POST",
        "path": "/invoices",
        "risk_level": "medium",
    }
    config = {
        "enabled_tools": [],
        "execution_mode": "dry-run",
        "audit_log_path": str(log_path),
    }
    policy = evaluate_tool_policy(tool, config)

    write_audit_event(
        build_audit_event(
            tool=tool,
            policy=policy,
            config=config,
            source="fastapi",
            action="policy_evaluation",
        )
    )

    events = read_events(log_path)

    assert events[0]["tool_name"] == "create_invoice"
    assert events[0]["status"] == "blocked"
    assert events[0]["allowed"] is False
    assert events[0]["action"] == "policy_evaluation"


def test_confirmation_required_is_logged(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "audit.log"
    tool = {
        "name": "create_invoice",
        "method": "POST",
        "path": "/invoices",
        "risk_level": "medium",
    }
    config = {
        "enabled_tools": ["create_invoice"],
        "execution_mode": "safe-execute",
        "audit_log_path": str(log_path),
    }
    policy = evaluate_tool_policy(tool, config, mode="safe-execute")

    write_audit_event(
        build_audit_event(
            tool=tool,
            policy=policy,
            config=config,
            source="mcp",
            action="policy_evaluation",
        )
    )

    events = read_events(log_path)

    assert events[0]["status"] == "confirmation_required"
    assert events[0]["source"] == "mcp"
    assert events[0]["allowed"] is False
