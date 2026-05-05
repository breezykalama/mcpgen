from mcpgen.runtime.metrics import record_metric


VALID_MODES = {"dry-run", "safe-execute"}
KNOWN_RISKS = {"low", "medium", "high"}


def evaluate_tool_policy(tool: dict, config: dict, mode: str = "dry-run") -> dict:
    """Evaluate whether a generated tool can be used under the active policy."""
    tool_name = tool.get("name") or tool.get("tool_name") or "unknown"
    risk_level = str(tool.get("risk_level", "unknown")).lower()
    method = str(tool.get("method", "")).upper()
    enabled_tools = set(config.get("enabled_tools") or [])
    active_mode = mode or config.get("execution_mode", "dry-run")

    if active_mode not in VALID_MODES:
        return finalize_decision(
            False,
            "blocked",
            f"Invalid execution mode: {active_mode}.",
            risk_level,
            tool_name,
            tool,
            config,
        )

    if risk_level not in KNOWN_RISKS:
        return finalize_decision(False, "blocked", "Unknown-risk tools are blocked.", risk_level, tool_name, tool, config)

    if risk_level == "high":
        return finalize_decision(False, "blocked", "High-risk tools are always blocked.", risk_level, tool_name, tool, config)

    if risk_level == "low" and method == "GET":
        return finalize_decision(True, "allowed", "Low-risk GET tool is allowed.", risk_level, tool_name, tool, config)

    if risk_level == "medium":
        if tool_name not in enabled_tools:
            return finalize_decision(
                False,
                "blocked",
                "Medium-risk tool is not listed in enabled_tools.",
                risk_level,
                tool_name,
                tool,
                config,
            )

        if active_mode == "safe-execute":
            return finalize_decision(
                False,
                "confirmation_required",
                "Medium-risk enabled tool requires confirmation before execution.",
                risk_level,
                tool_name,
                tool,
                config,
            )

        return finalize_decision(
            True,
            "allowed",
            "Medium-risk enabled tool is allowed for dry-run only.",
            risk_level,
            tool_name,
            tool,
            config,
        )

    return finalize_decision(False, "blocked", "Tool is blocked by policy.", risk_level, tool_name, tool, config)


def decision(allowed: bool, status: str, reason: str, risk_level: str, tool_name: str) -> dict:
    return {
        "allowed": allowed,
        "status": status,
        "reason": reason,
        "risk_level": risk_level,
        "tool_name": tool_name,
    }


def finalize_decision(
    allowed: bool,
    status: str,
    reason: str,
    risk_level: str,
    tool_name: str,
    tool: dict,
    config: dict,
) -> dict:
    result = decision(allowed, status, reason, risk_level, tool_name)
    record_metric(
        {
            "action": "policy_evaluation",
            "tool_name": tool_name,
            "method": tool.get("method", "unknown"),
            "path": tool.get("path", "unknown"),
            "risk_level": risk_level,
            "status": status,
            "allowed": allowed,
            "source": config.get("source", "runtime"),
        },
        config,
    )
    return result
