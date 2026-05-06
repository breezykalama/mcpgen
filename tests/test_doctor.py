from pathlib import Path

from mcpgen.core.doctor import run_doctor


def test_doctor_returns_pass_with_default_warnings() -> None:
    result = run_doctor(Path("examples/jsonplaceholder.openapi.yaml"))

    assert result["status"] == "warn"
    assert any(check["name"] == "openapi" and check["status"] == "pass" for check in result["checks"])
    assert any(check["name"] == "api_base_url" and check["status"] == "warn" for check in result["checks"])
    assert any(check["name"] == "tools" and check["status"] == "pass" for check in result["checks"])


def test_doctor_passes_with_production_like_config(tmp_path: Path) -> None:
    config_path = tmp_path / "mcpgen.yaml"
    config_path.write_text(
        """
        api_base_url: https://jsonplaceholder.typicode.com
        rate_limit:
          enabled: true
          per_tool: 10
          global: 100
          window_seconds: 60
        """,
        encoding="utf-8",
    )

    result = run_doctor(Path("examples/jsonplaceholder.openapi.yaml"), config_path=config_path)

    assert result["status"] == "pass"


def test_doctor_fails_invalid_config(tmp_path: Path) -> None:
    config_path = tmp_path / "mcpgen.yaml"
    config_path.write_text(
        """
        rate_limit:
          enabled: true
          per_tool: 0
          global: 100
          window_seconds: 60
        """,
        encoding="utf-8",
    )

    result = run_doctor(Path("examples/jsonplaceholder.openapi.yaml"), config_path=config_path)

    assert result["status"] == "fail"
    assert any(check["name"] == "rate_limit" and check["status"] == "fail" for check in result["checks"])
