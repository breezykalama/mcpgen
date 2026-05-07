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
    assert (output_dir / "tool_catalog.md").exists()


def test_init_command_writes_starter_files(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["init", "--directory", str(tmp_path), "--profile", "mock"])

    assert result.exit_code == 0
    assert "Initialized MCPGen project" in result.stdout
    assert (tmp_path / "mcpgen.yaml").exists()
    assert (tmp_path / ".env.example").exists()
    assert (tmp_path / "openapi.yaml").exists()
    assert (tmp_path / "routing_eval.yaml").exists()
    assert "mock:\n  enabled: true" in (tmp_path / "mcpgen.yaml").read_text(encoding="utf-8")


def test_init_command_refuses_existing_files_without_force(tmp_path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init", "--directory", str(tmp_path)])

    result = runner.invoke(app, ["init", "--directory", str(tmp_path)])

    assert result.exit_code == 1
    assert "Use --force" in result.stdout


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


def test_eval_routing_command_prints_summary(tmp_path) -> None:
    cases_path = tmp_path / "routing_eval.yaml"
    cases_path.write_text(
        """
        - query: list invoices
          expected:
            - list_invoices
        """,
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "eval-routing",
            "--from",
            "examples/openapi.yaml",
            "--cases",
            str(cases_path),
            "--top-k",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert "Routing eval: 1/1 passed" in result.stdout
    assert "[PASS] list invoices" in result.stdout


def test_eval_routing_command_exits_nonzero_on_failure(tmp_path) -> None:
    cases_path = tmp_path / "routing_eval.yaml"
    cases_path.write_text(
        """
        - query: list invoices
          expected:
            - list_customers
        """,
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "eval-routing",
            "--from",
            "examples/openapi.yaml",
            "--cases",
            str(cases_path),
            "--top-k",
            "1",
        ],
    )

    assert result.exit_code == 1
    assert "Routing eval: 0/1 passed" in result.stdout
    assert "[FAIL] list invoices" in result.stdout


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
