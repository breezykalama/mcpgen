from mcpgen.runtime.policy import evaluate_tool_policy


def test_low_risk_get_allowed_in_dry_run() -> None:
    decision = evaluate_tool_policy(
        {"name": "list_invoices", "method": "GET", "risk_level": "low"},
        {"enabled_tools": [], "execution_mode": "dry-run"},
    )

    assert decision == {
        "allowed": True,
        "status": "allowed",
        "reason": "Low-risk GET tool is allowed.",
        "risk_level": "low",
        "tool_name": "list_invoices",
    }


def test_medium_risk_not_enabled_blocked() -> None:
    decision = evaluate_tool_policy(
        {"name": "create_invoice", "method": "POST", "risk_level": "medium"},
        {"enabled_tools": [], "execution_mode": "dry-run"},
    )

    assert decision["allowed"] is False
    assert decision["status"] == "blocked"
    assert decision["reason"] == "Medium-risk tool is not listed in enabled_tools."


def test_medium_risk_enabled_requires_confirmation_in_safe_execute() -> None:
    decision = evaluate_tool_policy(
        {"name": "create_invoice", "method": "POST", "risk_level": "medium"},
        {"enabled_tools": ["create_invoice"], "execution_mode": "safe-execute"},
        mode="safe-execute",
    )

    assert decision["allowed"] is False
    assert decision["status"] == "confirmation_required"
    assert decision["reason"] == "Medium-risk enabled tool requires confirmation before execution."


def test_high_risk_blocked() -> None:
    decision = evaluate_tool_policy(
        {"name": "delete_invoice", "method": "DELETE", "risk_level": "high"},
        {"enabled_tools": ["delete_invoice"], "execution_mode": "dry-run"},
    )

    assert decision["allowed"] is False
    assert decision["status"] == "blocked"
    assert decision["reason"] == "High-risk tools are always blocked."


def test_invalid_mode_blocked() -> None:
    decision = evaluate_tool_policy(
        {"name": "list_invoices", "method": "GET", "risk_level": "low"},
        {"enabled_tools": [], "execution_mode": "execute"},
        mode="execute",
    )

    assert decision["allowed"] is False
    assert decision["status"] == "blocked"
    assert decision["reason"] == "Invalid execution mode: execute."
