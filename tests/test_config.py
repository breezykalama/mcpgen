from pathlib import Path

from mcpgen.core.config import MCPGenConfig, load_config


def test_default_config_is_safe() -> None:
    config = MCPGenConfig()

    assert config.max_tools == 5
    assert config.normalized_allowed_methods() == {"GET"}
    assert config.output_dir == "generated_mcp_server"
    assert config.api_base_url == "https://api.example.com"
    assert config.enabled_tools == []
    assert config.execution_mode == "dry-run"
    assert config.audit_enabled is True
    assert config.audit_log_path == "logs/audit.log"
    assert config.routing_mode == "semantic"


def test_load_config_from_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "mcpgen.yaml"
    config_path.write_text(
        """
        max_tools: 3
        allowed_methods:
          - get
        output_dir: custom_server
        api_base_url: https://billing.example.test
        enabled_tools:
          - create_invoice
        execution_mode: safe-execute
        audit_enabled: false
        audit_log_path: custom/audit.log
        routing_mode: keyword
        """,
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.max_tools == 3
    assert config.normalized_allowed_methods() == {"GET"}
    assert config.output_dir == "custom_server"
    assert config.api_base_url == "https://billing.example.test"
    assert config.enabled_tools == ["create_invoice"]
    assert config.execution_mode == "safe-execute"
    assert config.audit_enabled is False
    assert config.audit_log_path == "custom/audit.log"
    assert config.routing_mode == "keyword"
