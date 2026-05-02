from pathlib import Path
from typing import Optional

import typer

from mcpgen.core.config import load_config
from mcpgen.core.generator import generate_project
from mcpgen.core.inspector import inspect_spec

app = typer.Typer(help="Generate safe-by-default MCP-style servers from OpenAPI specs.")


@app.callback()
def main() -> None:
    """MCPGen command line interface."""


@app.command()
def generate(
    from_: Path = typer.Option(
        ...,
        "--from",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to an OpenAPI YAML or JSON file.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Directory for generated server files.",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to mcpgen.yaml config.",
    ),
    mode: str = typer.Option(
        "fastapi",
        "--mode",
        case_sensitive=False,
        help="Generated server mode: fastapi or mcp.",
    ),
) -> None:
    """Parse an OpenAPI spec and scaffold a runnable FastAPI tool server."""
    mode = mode.lower()
    if mode not in {"fastapi", "mcp"}:
        raise typer.BadParameter("mode must be 'fastapi' or 'mcp'")

    loaded_config = load_config(config)
    output_dir = output or Path(loaded_config.output_dir)
    result = generate_project(from_, output_dir, config=loaded_config, mode=mode)  # type: ignore[arg-type]

    typer.echo(f"Generated {len(result.tools)} safe tool(s).")
    typer.echo(f"Analyzed {len(result.all_tools)} total tool(s).")
    typer.echo(f"Mode: {result.mode}")
    typer.echo(f"Output directory: {result.output_dir}")
    typer.echo(
        "Wrote tools.json, tools.all.json, tools.embeddings.json, "
        "safety_report.json, mcpgen.runtime.json, and mcpgen.generated.yaml."
    )
    if mode == "fastapi":
        typer.echo("Run: uvicorn server:app --reload")
    else:
        typer.echo("Run: python server.py")


@app.command()
def inspect(
    from_: Path = typer.Option(
        ...,
        "--from",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to an OpenAPI YAML or JSON file.",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to mcpgen.yaml config.",
    ),
) -> None:
    """Inspect an OpenAPI spec and print safety/risk summary without generating files."""
    loaded_config = load_config(config)
    result = inspect_spec(from_, config=loaded_config)

    typer.echo(f"Total tools: {result['total_tools']}")
    typer.echo(f"Exposed tools: {result['exposed_tools']}")
    typer.echo(f"Withheld tools: {result['withheld_tools']}")
    typer.echo("")
    typer.echo("Risk breakdown:")
    typer.echo(f"- low: {result['risk_breakdown']['low']}")
    typer.echo(f"- medium: {result['risk_breakdown']['medium']}")
    typer.echo(f"- high: {result['risk_breakdown']['high']}")

    if result["withheld"]:
        typer.echo("")
        typer.echo("Withheld tools:")
        for tool in result["withheld"]:
            typer.echo(f"- {tool['name']} ({tool['method']} {tool['path']}): {tool['reason']}")


if __name__ == "__main__":
    app()
