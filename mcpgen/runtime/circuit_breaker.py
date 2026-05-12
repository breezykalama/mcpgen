from datetime import datetime, timezone
from time import time


_CIRCUITS: dict[str, dict] = {}


def check_circuit_breaker(tool_name: str, config: dict) -> dict:
    """Return whether execution should proceed for a tool."""
    circuit_config = config.get("circuit_breaker") or {}
    if circuit_config.get("enabled") is not True:
        return allowed_decision("disabled")

    state = _tool_state(tool_name)
    current_state = state.get("state", "closed")

    if current_state == "open":
        opened_at = state.get("opened_at") or 0.0
        recovery_seconds = int(circuit_config.get("recovery_seconds", 60))
        elapsed = time() - opened_at
        if elapsed >= recovery_seconds:
            state["state"] = "half_open"
            state["half_open_trial"] = True
            return allowed_decision("half_open")

        return {
            "allowed": False,
            "state": "open",
            "reason": "Circuit breaker is open.",
            **retry_metadata(max(1, int(recovery_seconds - elapsed))),
        }

    return allowed_decision(current_state)


def record_circuit_success(tool_name: str, config: dict) -> dict:
    if not circuit_enabled(config):
        return allowed_decision("disabled")

    state = _tool_state(tool_name)
    previous_state = state.get("state", "closed")
    state.update(
        {
            "state": "closed",
            "failure_count": 0,
            "opened_at": None,
            "half_open_trial": False,
        }
    )
    return {
        "state": "closed",
        "previous_state": previous_state,
        "changed": previous_state != "closed",
        "reason": "Circuit breaker closed after successful execution.",
    }


def record_circuit_failure(tool_name: str, config: dict) -> dict:
    if not circuit_enabled(config):
        return allowed_decision("disabled")

    circuit_config = config.get("circuit_breaker") or {}
    threshold = int(circuit_config.get("failure_threshold", 5))
    state = _tool_state(tool_name)
    previous_state = state.get("state", "closed")

    if previous_state == "half_open":
        open_circuit(state)
        retry_after = recovery_seconds(config)
        return {
            "state": "open",
            "previous_state": previous_state,
            "failure_count": state["failure_count"],
            "changed": True,
            "reason": "Circuit breaker reopened after half-open failure.",
            **retry_metadata(retry_after),
        }

    state["failure_count"] = int(state.get("failure_count", 0)) + 1
    if state["failure_count"] >= threshold:
        open_circuit(state)
        retry_after = recovery_seconds(config)
        return {
            "state": "open",
            "previous_state": previous_state,
            "failure_count": state["failure_count"],
            "changed": previous_state != "open",
            "reason": "Circuit breaker opened after repeated failures.",
            **retry_metadata(retry_after),
        }

    return {
        "state": state.get("state", "closed"),
        "previous_state": previous_state,
        "failure_count": state["failure_count"],
        "changed": False,
        "reason": "Circuit breaker failure count incremented.",
    }


def reset_circuit_breakers() -> None:
    _CIRCUITS.clear()


def circuit_enabled(config: dict) -> bool:
    return (config.get("circuit_breaker") or {}).get("enabled") is True


def recovery_seconds(config: dict) -> int:
    circuit_config = config.get("circuit_breaker") or {}
    return max(1, int(circuit_config.get("recovery_seconds", 60)))


def _tool_state(tool_name: str) -> dict:
    if tool_name not in _CIRCUITS:
        _CIRCUITS[tool_name] = {
            "state": "closed",
            "failure_count": 0,
            "opened_at": None,
            "half_open_trial": False,
        }
    return _CIRCUITS[tool_name]


def open_circuit(state: dict) -> None:
    state["state"] = "open"
    state["opened_at"] = time()
    state["half_open_trial"] = False


def allowed_decision(state: str) -> dict:
    return {
        "allowed": True,
        "state": state,
        "retry_after": 0,
        "reason": "Circuit breaker allows execution.",
    }


def retry_metadata(retry_after: int) -> dict:
    do_not_retry_until = datetime.fromtimestamp(time() + retry_after, tz=timezone.utc).isoformat()
    return {
        "retry_after": retry_after,
        "do_not_retry_until": do_not_retry_until,
        "agent_instruction": f"Do not retry this specific tool for at least {retry_after} seconds.",
    }
