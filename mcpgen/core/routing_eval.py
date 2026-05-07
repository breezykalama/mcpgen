from pathlib import Path
from typing import Any

import yaml

from mcpgen.core.config import MCPGenConfig
from mcpgen.core.parser import parse_openapi
from mcpgen.core.tool_generator import generate_tools
from mcpgen.core.tool_selection import apply_tool_selection
from mcpgen.runtime.embedding import generate_tool_embeddings
from mcpgen.runtime.router import rank_relevant_tools
from mcpgen.runtime.safety import filter_safe_tools


def evaluate_routing(
    spec_path: Path,
    cases_path: Path,
    config: MCPGenConfig | None = None,
    top_k: int | None = None,
) -> dict[str, Any]:
    """Evaluate whether natural-language queries route to expected safe tools."""
    config = config or MCPGenConfig()
    cases = load_routing_cases(cases_path)
    discovered_tools = generate_tools(parse_openapi(spec_path))
    selected_tools, selection_report = apply_tool_selection(discovered_tools, config)
    safe_tools = filter_safe_tools(selected_tools, allowed_methods=config.normalized_allowed_methods())
    limit = top_k or config.max_tools
    embeddings = generate_tool_embeddings(safe_tools) if config.routing_mode == "semantic" else []

    results = []
    for index, case in enumerate(cases, start=1):
        query = case["query"]
        expected = case["expected"]
        ranked = rank_relevant_tools(
            query,
            safe_tools,
            limit=limit,
            embeddings=embeddings,
            routing_mode=config.routing_mode,
        )
        returned = [item["tool"].name for item in ranked]
        matched = [tool_name for tool_name in expected if tool_name in returned]
        passed = len(matched) == len(expected)
        results.append(
            {
                "index": index,
                "query": query,
                "expected": expected,
                "returned": returned,
                "matched": matched,
                "passed": passed,
            }
        )

    passed_count = sum(1 for result in results if result["passed"])
    total = len(results)
    accuracy = passed_count / total if total else 0.0

    return {
        "status": "pass" if passed_count == total else "fail",
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "accuracy": accuracy,
        "routing_mode": config.routing_mode,
        "top_k": limit,
        "tool_counts": {
            "discovered": len(discovered_tools),
            "selected": len(selected_tools),
            "safe": len(safe_tools),
            "excluded": len(selection_report["excluded"]),
        },
        "results": results,
    }


def load_routing_cases(path: Path) -> list[dict[str, Any]]:
    raw_cases = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(raw_cases, list):
        raise ValueError("Routing eval cases must be a YAML list.")

    cases = []
    for index, item in enumerate(raw_cases, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Routing eval case {index} must be an object.")
        query = item.get("query")
        expected = item.get("expected")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"Routing eval case {index} must include a non-empty query.")
        if not isinstance(expected, list) or not expected or not all(isinstance(name, str) for name in expected):
            raise ValueError(f"Routing eval case {index} must include expected tool names.")
        cases.append({"query": query, "expected": expected})

    return cases
