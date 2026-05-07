# Changelog

All notable MCPGen changes are documented here.

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
