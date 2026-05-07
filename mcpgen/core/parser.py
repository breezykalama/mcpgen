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
                parameters=resolve_refs(operation.get("parameters", []), spec),
                request_body=resolve_refs(operation.get("requestBody"), spec),
                responses=resolve_refs(operation.get("responses", {}), spec),
            )
            endpoints.append(endpoint)

    return endpoints


def method_upper(method: str) -> str:
    return method.upper()


def resolve_refs(value: Any, spec: dict[str, Any], seen: set[str] | None = None) -> Any:
    """Resolve local OpenAPI $ref values inside dict/list structures."""
    seen = seen or set()

    if isinstance(value, list):
        return [resolve_refs(item, spec, seen.copy()) for item in value]

    if not isinstance(value, dict):
        return value

    ref = value.get("$ref")
    if isinstance(ref, str):
        resolved = resolve_local_ref(ref, spec)
        if resolved is None or ref in seen:
            return value
        seen.add(ref)
        merged = dict(resolved)
        for key, item in value.items():
            if key != "$ref":
                merged[key] = item
        return resolve_refs(merged, spec, seen)

    resolved = {key: resolve_refs(item, spec, seen.copy()) for key, item in value.items()}
    return merge_all_of(resolved)


def resolve_local_ref(ref: str, spec: dict[str, Any]) -> Any | None:
    if not ref.startswith("#/"):
        return None

    current: Any = spec
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def find_unresolved_refs(value: Any) -> list[str]:
    refs = []

    if isinstance(value, list):
        for item in value:
            refs.extend(find_unresolved_refs(item))
        return refs

    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            refs.append(ref)
        for item in value.values():
            refs.extend(find_unresolved_refs(item))

    return refs


def merge_all_of(schema: dict[str, Any]) -> dict[str, Any]:
    all_of = schema.get("allOf")
    if not isinstance(all_of, list):
        return schema

    merged: dict[str, Any] = {key: value for key, value in schema.items() if key != "allOf"}
    properties: dict[str, Any] = {}
    required: list[str] = []

    for item in all_of:
        if not isinstance(item, dict):
            continue
        properties.update(item.get("properties") or {})
        for field in item.get("required") or []:
            if field not in required:
                required.append(field)
        for key, value in item.items():
            if key not in {"properties", "required"}:
                merged.setdefault(key, value)

    if properties:
        merged["properties"] = {**(merged.get("properties") or {}), **properties}
    if required:
        merged["required"] = list(dict.fromkeys([*(merged.get("required") or []), *required]))
    merged.setdefault("type", "object")
    return merged
