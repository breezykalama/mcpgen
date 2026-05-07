import importlib.util
import tempfile
from pathlib import Path
from typing import Any

from mcpgen.core.config import MCPGenConfig
from mcpgen.core.doctor import run_doctor
from mcpgen.core.generator import generate_project
from mcpgen.core.inspector import inspect_spec
from mcpgen.core.routing_eval import evaluate_routing


REQUIRED_GENERATED_FILES = [
    "server.py",
    "tools.json",
    "tools.all.json",
    "tools.embeddings.json",
    "safety_report.json",
    "tool_catalog.md",
    "mcpgen.runtime.json",
    "mcpgen.generated.yaml",
    ".env.example",
]


def run_smoke_test(
    spec_path: Path,
    config: MCPGenConfig,
    config_path: Path | None = None,
    cases_path: Path | None = None,
    mode: str = "fastapi",
) -> dict[str, Any]:
    """Run a lightweight end-to-end confidence check."""
    checks = []

    doctor = run_doctor(spec_path, config_path=config_path)
    checks.append(check_from_status("doctor", doctor["status"], f"doctor completed with status {doctor['status']}"))

    inspection = inspect_spec(spec_path, config=config)
    if inspection["exposed_tools"] > 0:
        checks.append(pass_check("safe_tools", f"{inspection['exposed_tools']} safe tool(s) exposed."))
    else:
        checks.append(fail_check("safe_tools", "No safe tools are exposed."))

    if inspection["withheld_tools"] > 0:
        checks.append(pass_check("withheld_tools", f"{inspection['withheld_tools']} risky tool(s) withheld."))
    else:
        checks.append(warn_check("withheld_tools", "No risky tools are withheld; confirm the spec is read-only."))

    with tempfile.TemporaryDirectory(prefix="mcpgen-smoke-") as temp_dir:
        output_dir = Path(temp_dir) / "generated"
        generate_project(spec_path, output_dir, config=config, mode=mode)  # type: ignore[arg-type]
        checks.extend(generated_file_checks(output_dir))
        checks.extend(generated_server_checks(output_dir, mode=mode))

    if cases_path is not None:
        routing_eval = evaluate_routing(spec_path, cases_path, config=config)
        checks.append(
            check_from_status(
                "routing_eval",
                routing_eval["status"],
                f"{routing_eval['passed']}/{routing_eval['total']} routing case(s) passed.",
            )
        )

    status = "pass"
    if any(check["status"] == "fail" for check in checks):
        status = "fail"

    return {"status": status, "checks": checks}


def generated_file_checks(output_dir: Path) -> list[dict]:
    checks = []
    for filename in REQUIRED_GENERATED_FILES:
        path = output_dir / filename
        if path.exists():
            checks.append(pass_check("generated_file", f"{filename} exists."))
        else:
            checks.append(fail_check("generated_file", f"{filename} is missing."))
    return checks


def generated_server_checks(output_dir: Path, mode: str) -> list[dict]:
    module = load_generated_module(output_dir / "server.py")

    if mode == "fastapi":
        root = module.root()
        health = module.health()
        if root.get("status") == "ok" and health.get("status") == "ok":
            return [pass_check("generated_server", "FastAPI server module exposes root and health.")]
        return [fail_check("generated_server", "FastAPI server root/health check failed.")]

    listed = module.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    if "result" in listed and "tools" in listed["result"]:
        return [pass_check("generated_server", "MCP server module handles tools/list.")]
    return [fail_check("generated_server", "MCP server tools/list check failed.")]


def load_generated_module(path: Path):
    spec = importlib.util.spec_from_file_location("mcpgen_smoke_generated_server", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load generated server module.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_from_status(name: str, status: str, message: str) -> dict:
    if status == "pass":
        return pass_check(name, message)
    if status == "warn":
        return warn_check(name, message)
    return fail_check(name, message)


def pass_check(name: str, message: str) -> dict:
    return {"name": name, "status": "pass", "message": message}


def warn_check(name: str, message: str) -> dict:
    return {"name": name, "status": "warn", "message": message}


def fail_check(name: str, message: str) -> dict:
    return {"name": name, "status": "fail", "message": message}
