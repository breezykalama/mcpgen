from pathlib import Path

import pytest

from mcpgen.core.config import MCPGenConfig
from mcpgen.core.routing_eval import evaluate_routing, load_routing_cases


def test_evaluate_routing_passes_expected_tools(tmp_path: Path) -> None:
    cases_path = tmp_path / "routing_eval.yaml"
    cases_path.write_text(
        """
        - query: list invoices
          expected:
            - list_invoices
        - query: list customers
          expected:
            - list_customers
        """,
        encoding="utf-8",
    )

    result = evaluate_routing(
        Path("examples/openapi.yaml"),
        cases_path,
        config=MCPGenConfig(routing_mode="keyword"),
    )

    assert result["status"] == "pass"
    assert result["passed"] == 2
    assert result["accuracy"] == 1.0
    assert result["results"][0]["returned"][0] == "list_invoices"


def test_evaluate_routing_fails_missing_expected_tool(tmp_path: Path) -> None:
    cases_path = tmp_path / "routing_eval.yaml"
    cases_path.write_text(
        """
        - query: list invoices
          expected:
            - list_customers
        """,
        encoding="utf-8",
    )

    result = evaluate_routing(
        Path("examples/openapi.yaml"),
        cases_path,
        config=MCPGenConfig(routing_mode="keyword"),
        top_k=1,
    )

    assert result["status"] == "fail"
    assert result["failed"] == 1
    assert result["results"][0]["returned"] == ["list_invoices"]


def test_load_routing_cases_validates_shape(tmp_path: Path) -> None:
    cases_path = tmp_path / "routing_eval.yaml"
    cases_path.write_text("query: missing list\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_routing_cases(cases_path)
