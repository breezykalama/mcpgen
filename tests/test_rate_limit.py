from mcpgen.runtime.rate_limit import check_rate_limit, record_rate_limit_hit, reset_rate_limits


def test_disabled_rate_limiting_allows_requests() -> None:
    reset_rate_limits()
    decision = check_rate_limit("list_invoices", {"rate_limit": {"enabled": False}})

    assert decision["allowed"] is True


def test_reset_rate_limits_clears_hits() -> None:
    config = {
        "rate_limit": {
            "enabled": True,
            "per_tool": 1,
            "global": 10,
            "window_seconds": 60,
        }
    }
    reset_rate_limits()
    record_rate_limit_hit("list_invoices", config)

    assert check_rate_limit("list_invoices", config)["allowed"] is False

    reset_rate_limits()

    assert check_rate_limit("list_invoices", config)["allowed"] is True
