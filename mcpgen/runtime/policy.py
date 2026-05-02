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
        return decision(False, "blocked", f"Invalid execution mode: {active_mode}.", risk_level, tool_name)

    if risk_level not in KNOWN_RISKS:
        return decision(False, "blocked", "Unknown-risk tools are blocked.", risk_level, tool_name)

    if risk_level == "high":
        return decision(False, "blocked", "High-risk tools are always blocked.", risk_level, tool_name)

    if risk_level == "low" and method == "GET":
        return decision(True, "allowed", "Low-risk GET tool is allowed.", risk_level, tool_name)

    if risk_level == "medium":
        if tool_name not in enabled_tools:
            return decision(
                False,
                "blocked",
                "Medium-risk tool is not listed in enabled_tools.",
                risk_level,
                tool_name,
            )

        if active_mode == "safe-execute":
            return decision(
                False,
                "confirmation_required",
                "Medium-risk enabled tool requires confirmation before execution.",
                risk_level,
                tool_name,
            )

        return decision(
            True,
            "allowed",
            "Medium-risk enabled tool is allowed for dry-run only.",
            risk_level,
            tool_name,
        )

    return decision(False, "blocked", "Tool is blocked by policy.", risk_level, tool_name)


def decision(allowed: bool, status: str, reason: str, risk_level: str, tool_name: str) -> dict:
    return {
        "allowed": allowed,
        "status": status,
        "reason": reason,
        "risk_level": risk_level,
        "tool_name": tool_name,
    }
