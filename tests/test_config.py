from pathlib import Path

from mcpgen.core.config import MCPGenConfig, load_config


def test_default_config_is_safe() -> None:
    config = MCPGenConfig()

    assert config.max_tools == 5
    assert config.normalized_allowed_methods() == {"GET"}
    assert config.include_tools == []
    assert config.exclude_tools == []
    assert config.include_paths == []
    assert config.exclude_paths == []
    assert config.include_methods == []
    assert config.exclude_methods == []
    assert config.normalized_include_methods() == set()
    assert config.normalized_exclude_methods() == set()
    assert config.output_dir == "generated_mcp_server"
    assert config.api_base_url == "https://api.example.com"
    assert config.enabled_tools == []
    assert config.execution_mode == "dry-run"
    assert config.audit_enabled is True
    assert config.audit_log_path == "logs/audit.log"
    assert config.routing_mode == "semantic"
    assert config.metrics_enabled is True
    assert config.metrics_path == "logs/metrics.json"
    assert config.auth.mode == "none"
    assert config.auth.api_key_env == "API_KEY"
    assert config.auth.api_key_header == "X-API-Key"
    assert config.rate_limit.enabled is False
    assert config.rate_limit.per_tool == 10
    assert config.rate_limit.global_ == 100
    assert config.rate_limit.window_seconds == 60
    assert config.mock.enabled is False
    assert config.mock.mode == "schema"
    assert config.mock.seed == 123
    assert config.mock.list_size == 3
    assert config.failure_injection.enabled is False
    assert config.failure_injection.scenarios == {}
    assert config.circuit_breaker.enabled is False
    assert config.circuit_breaker.failure_threshold == 5
    assert config.circuit_breaker.recovery_seconds == 60
    assert config.retry.enabled is False
    assert config.retry.max_attempts == 3
    assert config.retry.backoff_seconds == 0.5
    assert config.retry.retry_statuses == [429, 500, 502, 503, 504]


def test_load_config_from_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "mcpgen.yaml"
    config_path.write_text(
        """
        max_tools: 3
        allowed_methods:
          - get
        include_tools:
          - list_invoices
        exclude_tools:
          - delete_invoice
        include_paths:
          - /invoices*
        exclude_paths:
          - /internal/*
        include_methods:
          - get
        exclude_methods:
          - delete
        output_dir: custom_server
        api_base_url: https://billing.example.test
        enabled_tools:
          - create_invoice
        execution_mode: safe-execute
        audit_enabled: false
        audit_log_path: custom/audit.log
        routing_mode: keyword
        metrics_enabled: false
        metrics_path: custom/metrics.json
        auth:
          mode: api_key
          api_key_env: BILLING_API_KEY
          api_key_header: X-Billing-Key
        rate_limit:
          enabled: true
          per_tool: 2
          global: 5
          window_seconds: 30
        mock:
          enabled: true
          mode: schema
          seed: 99
          list_size: 2
        failure_injection:
          enabled: true
          scenarios:
            list_invoices: timeout
        circuit_breaker:
          enabled: true
          failure_threshold: 2
          recovery_seconds: 30
        retry:
          enabled: true
          max_attempts: 4
          backoff_seconds: 0.1
          retry_statuses:
            - 500
            - 503
        """,
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.max_tools == 3
    assert config.normalized_allowed_methods() == {"GET"}
    assert config.include_tools == ["list_invoices"]
    assert config.exclude_tools == ["delete_invoice"]
    assert config.include_paths == ["/invoices*"]
    assert config.exclude_paths == ["/internal/*"]
    assert config.include_methods == ["get"]
    assert config.exclude_methods == ["delete"]
    assert config.normalized_include_methods() == {"GET"}
    assert config.normalized_exclude_methods() == {"DELETE"}
    assert config.output_dir == "custom_server"
    assert config.api_base_url == "https://billing.example.test"
    assert config.enabled_tools == ["create_invoice"]
    assert config.execution_mode == "safe-execute"
    assert config.audit_enabled is False
    assert config.audit_log_path == "custom/audit.log"
    assert config.routing_mode == "keyword"
    assert config.metrics_enabled is False
    assert config.metrics_path == "custom/metrics.json"
    assert config.auth.mode == "api_key"
    assert config.auth.api_key_env == "BILLING_API_KEY"
    assert config.auth.api_key_header == "X-Billing-Key"
    assert config.rate_limit.enabled is True
    assert config.rate_limit.per_tool == 2
    assert config.rate_limit.global_ == 5
    assert config.rate_limit.window_seconds == 30
    assert config.mock.enabled is True
    assert config.mock.seed == 99
    assert config.mock.list_size == 2
    assert config.failure_injection.enabled is True
    assert config.failure_injection.scenarios == {"list_invoices": "timeout"}
    assert config.circuit_breaker.enabled is True
    assert config.circuit_breaker.failure_threshold == 2
    assert config.circuit_breaker.recovery_seconds == 30
    assert config.retry.enabled is True
    assert config.retry.max_attempts == 4
    assert config.retry.backoff_seconds == 0.1
    assert config.retry.retry_statuses == [500, 503]
