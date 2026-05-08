import json
import shutil
from pathlib import Path
from typing import Literal

from mcpgen.core.catalog import write_tool_catalog
from mcpgen.core.config import MCPGenConfig, dump_runtime_config
from mcpgen.core.models import GenerationResult, Tool, model_to_dict
from mcpgen.core.parser import parse_openapi
from mcpgen.core.tool_selection import apply_tool_selection
from mcpgen.core.tool_generator import generate_tools
from mcpgen.runtime.embedding import generate_tool_embeddings
from mcpgen.runtime.safety import build_safety_report, filter_safe_tools


GenerateMode = Literal["fastapi", "mcp"]


def generate_project(
    spec_path: Path,
    output_dir: Path,
    config: MCPGenConfig | None = None,
    mode: GenerateMode = "fastapi",
) -> GenerationResult:
    """Generate tools.json and a runnable server scaffold."""
    config = config or MCPGenConfig()
    endpoints = parse_openapi(spec_path)
    discovered_tools = generate_tools(endpoints)
    all_tools, selection_report = apply_tool_selection(discovered_tools, config)
    allowed_methods = config.normalized_allowed_methods()
    tools = filter_safe_tools(all_tools, allowed_methods=allowed_methods)
    safety_report = build_safety_report(all_tools, tools, allowed_methods=allowed_methods)
    safety_report["selection"] = selection_report

    output_dir.mkdir(parents=True, exist_ok=True)
    write_tools_json(tools, output_dir / "tools.json")
    write_tools_json(all_tools, output_dir / "tools.all.json")
    write_json(generate_tool_embeddings(all_tools), output_dir / "tools.embeddings.json")
    write_json(safety_report, output_dir / "safety_report.json")
    write_tool_catalog(all_tools, tools, output_dir / "tool_catalog.md")
    write_json(dump_runtime_config(config, mode=mode), output_dir / "mcpgen.runtime.json")
    write_env_example(config, output_dir / ".env.example")
    write_generated_config(config, mode, output_dir / "mcpgen.generated.yaml")
    copy_server_template(output_dir / "server.py", mode=mode)

    return GenerationResult(
        output_dir=str(output_dir.resolve()),
        tools=tools,
        mode=mode,
        all_tools=all_tools,
        safety_report=safety_report,
    )


def write_tools_json(tools: list[Tool], path: Path) -> None:
    data = [model_to_dict(tool, mode="json") for tool in tools]
    write_json(data, path)


def write_json(data: object, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_env_example(config: MCPGenConfig, path: Path) -> None:
    path.write_text(f"API_BASE_URL={config.api_base_url}\n", encoding="utf-8")


def write_generated_config(config: MCPGenConfig, mode: str, path: Path) -> None:
    data = {
        "mode": mode,
        "max_tools": config.max_tools,
        "allowed_methods": sorted(config.normalized_allowed_methods()),
        "include_tools": config.include_tools,
        "exclude_tools": config.exclude_tools,
        "include_paths": config.include_paths,
        "exclude_paths": config.exclude_paths,
        "include_methods": sorted(config.normalized_include_methods()),
        "exclude_methods": sorted(config.normalized_exclude_methods()),
        "output_dir": config.output_dir,
        "api_base_url": config.api_base_url,
        "enabled_tools": config.enabled_tools,
        "execution_mode": config.execution_mode,
        "audit_enabled": config.audit_enabled,
        "audit_log_path": config.audit_log_path,
        "routing_mode": config.routing_mode,
        "metrics_enabled": config.metrics_enabled,
        "metrics_path": config.metrics_path,
        "auth": model_to_dict(config.auth),
        "rate_limit": model_to_dict(config.rate_limit, by_alias=True),
        "mock": model_to_dict(config.mock),
        "failure_injection": model_to_dict(config.failure_injection),
        "circuit_breaker": model_to_dict(config.circuit_breaker),
    }
    path.write_text(json_to_yaml_like(data), encoding="utf-8")


def json_to_yaml_like(data: dict) -> str:
    lines = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in value)
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            lines.extend(f"  {item_key}: {item_value}" for item_key, item_value in value.items())
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"


def copy_server_template(destination: Path, mode: GenerateMode = "fastapi") -> None:
    template_name = "fastapi_server.py" if mode == "fastapi" else "mcp_server.py"
    template_path = Path(__file__).resolve().parents[1] / "templates" / template_name
    shutil.copyfile(template_path, destination)
