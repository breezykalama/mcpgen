from pathlib import Path

import pytest

from mcpgen.core.init_project import init_project


def test_init_project_writes_starter_files(tmp_path: Path) -> None:
    written = init_project(tmp_path, profile="safe")

    assert tmp_path / "mcpgen.yaml" in written
    assert tmp_path / ".env.example" in written
    assert tmp_path / "openapi.yaml" in written
    assert "mock:\n  enabled: false" in (tmp_path / "mcpgen.yaml").read_text(encoding="utf-8")
    assert "API_BASE_URL=https://jsonplaceholder.typicode.com" in (tmp_path / ".env.example").read_text(
        encoding="utf-8"
    )
    assert "operationId: listUsers" in (tmp_path / "openapi.yaml").read_text(encoding="utf-8")


def test_init_project_mock_profile_enables_mock_mode(tmp_path: Path) -> None:
    init_project(tmp_path, profile="mock")

    assert "mock:\n  enabled: true" in (tmp_path / "mcpgen.yaml").read_text(encoding="utf-8")


def test_init_project_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    init_project(tmp_path)

    with pytest.raises(FileExistsError):
        init_project(tmp_path)


def test_init_project_force_overwrites_files(tmp_path: Path) -> None:
    init_project(tmp_path)
    (tmp_path / "mcpgen.yaml").write_text("changed: true\n", encoding="utf-8")

    init_project(tmp_path, force=True)

    assert "changed: true" not in (tmp_path / "mcpgen.yaml").read_text(encoding="utf-8")


def test_init_project_rejects_unknown_profile(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        init_project(tmp_path, profile="unknown")
