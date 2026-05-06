from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class AuthConfig(BaseModel):
    mode: str = "none"
    api_key_env: str = "API_KEY"
    api_key_header: str = "X-API-Key"


class RateLimitConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = False
    per_tool: int = 10
    global_: int = Field(default=100, alias="global")
    window_seconds: int = 60


class MockConfig(BaseModel):
    enabled: bool = False
    mode: str = "schema"
    seed: int = 123
    list_size: int = 3


class FailureInjectionConfig(BaseModel):
    enabled: bool = False
    scenarios: dict[str, str] = Field(default_factory=dict)


class MCPGenConfig(BaseModel):
    """Small, safe-by-default generation config."""

    max_tools: int = 5
    allowed_methods: list[str] = Field(default_factory=lambda: ["GET"])
    output_dir: str = "generated_mcp_server"
    api_base_url: str = "https://api.example.com"
    enabled_tools: list[str] = Field(default_factory=list)
    execution_mode: str = "dry-run"
    audit_enabled: bool = True
    audit_log_path: str = "logs/audit.log"
    routing_mode: str = "semantic"
    metrics_enabled: bool = True
    metrics_path: str = "logs/metrics.json"
    auth: AuthConfig = Field(default_factory=AuthConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    mock: MockConfig = Field(default_factory=MockConfig)
    failure_injection: FailureInjectionConfig = Field(default_factory=FailureInjectionConfig)

    def normalized_allowed_methods(self) -> set[str]:
        return {method.upper() for method in self.allowed_methods}


def load_config(path: Path | None = None) -> MCPGenConfig:
    """Load config from an explicit path, local mcpgen.yaml, or defaults."""
    config_path = path or default_config_path()
    if config_path is None:
        return MCPGenConfig()

    raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return MCPGenConfig.model_validate(raw_config)


def default_config_path() -> Path | None:
    for name in ("mcpgen.yaml", "mcpgen.yml"):
        candidate = Path(name)
        if candidate.exists():
            return candidate
    return None


def dump_runtime_config(config: MCPGenConfig, mode: str = "fastapi") -> dict[str, Any]:
    return {
        "mode": mode,
        "max_tools": config.max_tools,
        "allowed_methods": sorted(config.normalized_allowed_methods()),
        "api_base_url": config.api_base_url,
        "enabled_tools": config.enabled_tools,
        "execution_mode": config.execution_mode,
        "audit_enabled": config.audit_enabled,
        "audit_log_path": config.audit_log_path,
        "routing_mode": config.routing_mode,
        "metrics_enabled": config.metrics_enabled,
        "metrics_path": config.metrics_path,
        "auth": config.auth.model_dump(),
        "rate_limit": config.rate_limit.model_dump(by_alias=True),
        "mock": config.mock.model_dump(),
        "failure_injection": config.failure_injection.model_dump(),
    }
