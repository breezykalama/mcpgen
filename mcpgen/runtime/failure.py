SUPPORTED_FAILURE_SCENARIOS = {"timeout", "not_found", "server_error", "malformed_json"}


def get_failure_scenario(tool_name: str, config: dict) -> str | None:
    failure_config = config.get("failure_injection") or {}
    if failure_config.get("enabled") is not True:
        return None

    scenario = (failure_config.get("scenarios") or {}).get(tool_name)
    if scenario in SUPPORTED_FAILURE_SCENARIOS:
        return scenario
    return None


def build_failure_response(tool_name: str, scenario: str) -> dict:
    if scenario == "timeout":
        return simulated_error(tool_name, None, "Simulated upstream timeout.")
    if scenario == "not_found":
        return simulated_error(tool_name, 404, "Simulated not found.")
    if scenario == "server_error":
        return simulated_error(tool_name, 500, "Simulated upstream server error.")
    if scenario == "malformed_json":
        return simulated_error(tool_name, 502, "Simulated malformed JSON response.")
    return simulated_error(tool_name, None, f"Unsupported failure scenario: {scenario}.")


def simulated_error(tool_name: str, status_code: int | None, message: str) -> dict:
    return {
        "tool": tool_name,
        "status": "error",
        "status_code": status_code,
        "data": {
            "error": message,
        },
        "simulated": True,
    }
