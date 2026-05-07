from typer.testing import CliRunner

from mcpgen.cli.main import app


def test_generate_command_defaults_to_fastapi(tmp_path) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "server"

    result = runner.invoke(app, ["generate", "--from", "examples/openapi.yaml", "--output", str(output_dir)])

    assert result.exit_code == 0
    assert "Mode: fastapi" in result.stdout
    assert "Run: uvicorn server:app --reload" in result.stdout
    assert (output_dir / "server.py").exists()


def test_generate_command_supports_fastapi_mode(tmp_path) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "server"

    result = runner.invoke(
        app,
        ["generate", "--from", "examples/openapi.yaml", "--output", str(output_dir), "--mode", "fastapi"],
    )

    assert result.exit_code == 0
    assert "Mode: fastapi" in result.stdout


def test_generate_command_supports_mcp_mode(tmp_path) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "server"

    result = runner.invoke(
        app,
        ["generate", "--from", "examples/openapi.yaml", "--output", str(output_dir), "--mode", "mcp"],
    )

    assert result.exit_code == 0
    assert "Mode: mcp" in result.stdout
    assert "Run: python server.py" in result.stdout


def test_inspect_command_prints_summary() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["inspect", "--from", "examples/openapi.yaml"])

    assert result.exit_code == 0
    assert "Total tools: 5" in result.stdout
    assert "Selected tools: 5" in result.stdout
    assert "Excluded tools: 0" in result.stdout
    assert "Exposed tools: 2" in result.stdout
    assert "Withheld tools: 3" in result.stdout
    assert "- high: 1" in result.stdout
    assert "delete_invoice" in result.stdout


def test_doctor_command_prints_diagnostics() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["doctor", "--from", "examples/jsonplaceholder.openapi.yaml"])

    assert result.exit_code == 0
    assert "MCPGen doctor: warn" in result.stdout
    assert "[PASS] openapi:" in result.stdout
    assert "[WARN] api_base_url:" in result.stdout


def test_doctor_command_exits_nonzero_on_failure(tmp_path) -> None:
    config_path = tmp_path / "mcpgen.yaml"
    config_path.write_text(
        """
        rate_limit:
          enabled: true
          per_tool: 0
        """,
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["doctor", "--from", "examples/jsonplaceholder.openapi.yaml", "--config", str(config_path)],
    )

    assert result.exit_code == 1
    assert "[FAIL] rate_limit:" in result.stdout
