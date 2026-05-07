from pathlib import Path
from typing import Optional

import typer

from mcpgen.core.config import load_config
from mcpgen.core.doctor import run_doctor
from mcpgen.core.generator import generate_project
from mcpgen.core.init_project import init_project
from mcpgen.core.inspector import inspect_spec
from mcpgen.core.routing_eval import evaluate_routing

app = typer.Typer(help="Generate safe-by-default MCP-style servers from OpenAPI specs.")


@app.callback()
def main() -> None:
    """MCPGen command line interface."""


@app.command()
def init(
    directory: Path = typer.Option(
        Path("."),
        "--directory",
        "-d",
        help="Directory where starter files should be written.",
    ),
    profile: str = typer.Option(
        "safe",
        "--profile",
        case_sensitive=False,
        help="Starter profile: safe or mock.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing starter files.",
    ),
) -> None:
    """Create starter MCPGen config, env, and OpenAPI files."""
    try:
        written = init_project(directory, profile=profile, force=force)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except FileExistsError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    typer.echo(f"Initialized MCPGen project in {directory.resolve()}")
    for path in written:
        typer.echo(f"- {path}")
    typer.echo("")
    typer.echo("Next:")
    typer.echo(f"mcpgen doctor --from {directory / 'openapi.yaml'} --config {directory / 'mcpgen.yaml'}")
    typer.echo(f"mcpgen generate --from {directory / 'openapi.yaml'} --config {directory / 'mcpgen.yaml'}")


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
        "safety_report.json, tool_catalog.md, mcpgen.runtime.json, and mcpgen.generated.yaml."
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
    typer.echo(f"Selected tools: {result['selected_tools']}")
    typer.echo(f"Excluded tools: {result['excluded_tools']}")
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

    if result["excluded"]:
        typer.echo("")
        typer.echo("Excluded by selection:")
        for tool in result["excluded"]:
            typer.echo(f"- {tool['name']} ({tool['method']} {tool['path']}): {tool['reason']}")


@app.command()
def eval_routing(
    from_: Path = typer.Option(
        ...,
        "--from",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to an OpenAPI YAML or JSON file.",
    ),
    cases: Path = typer.Option(
        ...,
        "--cases",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to routing eval YAML cases.",
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
    top_k: Optional[int] = typer.Option(
        None,
        "--top-k",
        min=1,
        help="Number of routed tools to evaluate per query. Defaults to max_tools.",
    ),
) -> None:
    """Evaluate routing quality against expected tool names."""
    loaded_config = load_config(config)
    result = evaluate_routing(from_, cases, config=loaded_config, top_k=top_k)

    typer.echo(f"Routing eval: {result['passed']}/{result['total']} passed")
    typer.echo(f"Accuracy: {result['accuracy']:.0%}")
    typer.echo(f"Routing mode: {result['routing_mode']}")
    typer.echo(f"Top K: {result['top_k']}")

    for case_result in result["results"]:
        status = "PASS" if case_result["passed"] else "FAIL"
        typer.echo("")
        typer.echo(f"[{status}] {case_result['query']}")
        typer.echo(f"Expected: {', '.join(case_result['expected'])}")
        typer.echo(f"Returned: {', '.join(case_result['returned']) or '(none)'}")

    if result["status"] == "fail":
        raise typer.Exit(code=1)


@app.command()
def doctor(
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
    """Run read-only diagnostics for an OpenAPI spec and MCPGen config."""
    result = run_doctor(from_, config_path=config)

    typer.echo(f"MCPGen doctor: {result['status']}")
    for check in result["checks"]:
        typer.echo(f"[{check['status'].upper()}] {check['name']}: {check['message']}")

    if result["status"] == "fail":
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
