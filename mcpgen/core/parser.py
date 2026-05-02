import json
from pathlib import Path
from typing import Any

import yaml

from mcpgen.core.models import Endpoint

SUPPORTED_METHODS = {"get", "post", "put", "patch", "delete"}


def load_openapi_spec(path: Path) -> dict[str, Any]:
    """Load an OpenAPI spec from JSON or YAML."""
    content = path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".json":
        return json.loads(content)

    return yaml.safe_load(content)


def parse_openapi(path: Path) -> list[Endpoint]:
    """Parse OpenAPI paths into normalized endpoint models."""
    spec = load_openapi_spec(path)
    paths = spec.get("paths", {})
    endpoints: list[Endpoint] = []

    for route_path, operations in paths.items():
        if not isinstance(operations, dict):
            continue

        for method, operation in operations.items():
            method_lower = method.lower()
            if method_lower not in SUPPORTED_METHODS or not isinstance(operation, dict):
                continue

            endpoint = Endpoint(
                operation_id=operation.get("operationId"),
                summary=operation.get("summary"),
                description=operation.get("description"),
                method=method_upper(method_lower),
                path=route_path,
                parameters=operation.get("parameters", []),
                request_body=operation.get("requestBody"),
            )
            endpoints.append(endpoint)

    return endpoints


def method_upper(method: str) -> str:
    return method.upper()

