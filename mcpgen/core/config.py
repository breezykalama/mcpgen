from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


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
    }
