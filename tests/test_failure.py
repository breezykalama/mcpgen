from mcpgen.runtime.failure import build_failure_response, get_failure_scenario


def test_get_failure_scenario_returns_configured_scenario() -> None:
    scenario = get_failure_scenario(
        "get_user_by_id",
        {
            "failure_injection": {
                "enabled": True,
                "scenarios": {"get_user_by_id": "not_found"},
            }
        },
    )

    assert scenario == "not_found"


def test_get_failure_scenario_ignores_disabled_config() -> None:
    scenario = get_failure_scenario(
        "get_user_by_id",
        {
            "failure_injection": {
                "enabled": False,
                "scenarios": {"get_user_by_id": "not_found"},
            }
        },
    )

    assert scenario is None


def test_build_failure_response_not_found() -> None:
    result = build_failure_response("get_user_by_id", "not_found")

    assert result == {
        "tool": "get_user_by_id",
        "status": "error",
        "status_code": 404,
        "data": {
            "error": "Simulated not found.",
        },
        "simulated": True,
    }


def test_build_failure_response_timeout() -> None:
    result = build_failure_response("list_posts", "timeout")

    assert result["status"] == "error"
    assert result["status_code"] is None
    assert result["simulated"] is True
