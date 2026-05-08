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

        retry_after = max(1, int(recovery_seconds - elapsed))
        return {
            "allowed": False,
            "state": "open",
            "retry_after": retry_after,
            "reason": "Circuit breaker is open.",
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
        return {
            "state": "open",
            "previous_state": previous_state,
            "failure_count": state["failure_count"],
            "changed": True,
            "reason": "Circuit breaker reopened after half-open failure.",
        }

    state["failure_count"] = int(state.get("failure_count", 0)) + 1
    if state["failure_count"] >= threshold:
        open_circuit(state)
        return {
            "state": "open",
            "previous_state": previous_state,
            "failure_count": state["failure_count"],
            "changed": previous_state != "open",
            "reason": "Circuit breaker opened after repeated failures.",
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
