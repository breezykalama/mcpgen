# Changelog

All notable MCPGen changes are documented here.

## 1.6.0 - 2026-05-07

### Added

- Added in-memory per-tool circuit breaker runtime protection.
- Circuit breakers fail fast with `503` after repeated upstream failures.
- Added audit and metrics events for circuit breaker opened/blocked states.
- Added `circuit_breaker` config.

## 1.5.0 - 2026-05-07

### Added

- Added `mcpgen watchdog` for OpenAPI spec drift detection.
- Added `mcpgen.baseline.json` generation through `--write-baseline`.
- Watchdog compares tool names, methods, paths, risk levels, input schemas, response schemas, and exposure status.
- Watchdog runs smoke checks and optional routing evals.

## 1.4.0 - 2026-05-07

### Added

- Added MVP response validation against generated `response_schema`.
- Execution and mock responses now include `response_validation` metadata when applicable.
- Response validation checks required fields, basic types, enums, arrays, and nested objects.

## 1.3.0 - 2026-05-07

### Added

- Added `mcpgen smoke` for end-to-end generation confidence checks.
- Added an example gallery with JSONPlaceholder, GitHub-like, and billing API scenarios.
- Added CI matrix for Python 3.10, 3.11, and 3.12.
- Added CI smoke checks for example scenarios.
- Added security policy and config compatibility documentation.

## 1.2.0 - 2026-05-07

### Added

- Added `mcpgen eval-routing` for measuring query-to-tool routing quality.
- Added YAML routing eval cases with expected tool names.
- Added starter `routing_eval.yaml` from `mcpgen init`.
- Added CI-friendly nonzero exit code when routing eval cases fail.

## 1.1.0 - 2026-05-07

### Added

- Added `mcpgen init` to scaffold starter `mcpgen.yaml`, `.env.example`, and `openapi.yaml` files.
- Added safe and mock starter profiles for onboarding.
- Generated `tool_catalog.md` for human-readable tool review.

## 1.0.0 - 2026-05-07

### Added

- Stabilized the current production-oriented MVP feature set.
- Added root MIT `LICENSE`.
- Added PyPI metadata including project URLs, keywords, and classifiers.
- Added this changelog.
- Updated the checked-in `mcpgen.yaml` example to include the full current config surface.

### Stable MVP Surface

- OpenAPI YAML/JSON parsing.
- Safe-by-default tool generation and risk classification.
- FastAPI and MCP stdio generation modes.
- Policy engine, dry-run previews, and safe GET execution only.
- Audit logging and file-based metrics.
- Semantic routing with keyword fallback.
- Auth passthrough/API key injection.
- In-memory rate limiting.
- Runtime input validation.
- Mock runtime and failure injection.
- Tool selection controls.
- Local OpenAPI `$ref` resolution and response schema extraction.

## 0.9.0 - 2026-05-07

### Added

- Local OpenAPI `$ref` resolution for refs such as `#/components/schemas/User`.
- Simple `allOf` object merging.
- Response schema extraction into generated tools.
- Response-schema-aware mock responses.
- `doctor` warnings for unresolved refs.

## 0.8.0 - 2026-05-07

### Added

- Tool selection controls by name, path, and method.
- Selection reporting in `inspect`.
- Selection diagnostics in `doctor`.

## 0.7.0 - 2026-05-07

### Added

- Mock runtime for offline development.
- Failure injection for timeout, not found, server error, and malformed JSON scenarios.

## 0.6.0 - 2026-05-07

### Added

- Runtime input validation for required fields, basic JSON Schema types, and enums.
- `mcpgen doctor` diagnostics.

## 0.5.0 - 2026-05-07

### Added

- In-memory rate limiting for generated FastAPI servers and MCP tools/call.

## 0.4.0 - 2026-05-07

### Added

- Bearer token passthrough.
- API key header injection.
- Audit/metrics protection against credential leakage.

## 0.3.0 - 2026-05-07

### Added

- File-based runtime metrics.
- FastAPI `/metrics` and `/metrics/reset` endpoints.

## 0.2.0 - 2026-05-07

### Added

- Semantic routing with local embeddings and keyword fallback.
- Generated `tools.embeddings.json`.

## 0.1.0 - 2026-05-07

### Added

- Initial safe OpenAPI-to-MCP generator.
- FastAPI and MCP generation modes.
- Safety reports, dry-run previews, and CLI commands.
