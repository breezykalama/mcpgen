# MCPGen

**Generate secure, policy-aware MCP servers from OpenAPI specs.**

MCPGen is a production-oriented MVP Python framework that turns OpenAPI specifications into safe-by-default tool servers. It can generate a FastAPI demo server or an MCP-style stdio server, while keeping write operations blocked unless future policy work explicitly enables them.

## Problem

AI applications often need access to many APIs, databases, and internal systems. Without a framework, teams tend to rebuild the same integrations repeatedly, expose too many tools to the model, and skip safety controls such as risk classification, audit logs, and write-operation guardrails.

MCP servers make tools available to AI systems, but fast prototypes can accidentally expose dangerous operations like `DELETE`, `POST`, `PATCH`, or `PUT` without review.

## Solution

MCPGen reads an OpenAPI YAML or JSON file and generates:

- structured tool descriptors
- safe exposed tool lists
- withheld tool reports
- input schemas
- a policy-aware FastAPI or MCP server
- dry-run previews
- safe `GET` execution
- JSONL audit logs
- file-based runtime metrics
- semantic tool routing with keyword fallback

The default behavior is intentionally conservative: only low-risk `GET` tools are exposed.

## Status

MCPGen `1.0.0` is a stable production-oriented MVP. The current config keys, CLI commands, generated file names, and safe-by-default execution model are intended to be the first stable developer contract.

Stable in this MVP:

- `mcpgen init`, `mcpgen generate`, `mcpgen inspect`, `mcpgen doctor`, and `mcpgen eval-routing`
- FastAPI and MCP stdio generation modes
- generated `tools.json`, `tools.all.json`, `tools.embeddings.json`, `safety_report.json`, `tool_catalog.md`, and `mcpgen.runtime.json`
- safe GET execution only
- policy, audit, metrics, auth passthrough/API key injection, rate limiting, validation, mocks, failure injection, tool selection, and local schema refs
- routing evaluation for query-to-tool regression checks
- smoke tests for generated servers and example scenarios
- a documented `1.x` config compatibility contract

Still experimental:

- semantic embedding quality and embedding model selection
- MCP stdio scaffold details
- complex OpenAPI schema composition
- mock data realism
- file-based observability for production operations

## Features

- OpenAPI YAML/JSON parsing
- Starter project scaffolding with `mcpgen init`
- Tool generation from endpoints
- Developer-controlled tool selection by name, path, and method
- Risk classification:
  - `GET` = low
  - `POST`, `PUT`, `PATCH` = medium
  - `DELETE` = high
- Safe-by-default filtering
- Input schema generation from path/query parameters and JSON request bodies
- Local `$ref` resolution for OpenAPI components
- Response schema extraction for generated tools
- Semantic tool routing with keyword fallback
- FastAPI mode
- MCP stdio mode with `tools/list` and `tools/call`
- Dry-run request previews
- Safe real execution for low-risk `GET` tools only
- Central policy engine
- JSONL audit logging
- Runtime metrics for routing, policy decisions, dry-runs, execution outcomes, and latency
- Upstream auth passthrough and API key injection without hardcoded secrets
- Lightweight in-memory rate limiting
- Runtime input validation for required fields, basic types, and enums
- Response validation metadata for generated response schemas
- `doctor` diagnostics for specs and config readiness
- Mock execution and failure injection for offline development
- Human-readable generated tool catalog
- Routing evaluation for semantic/keyword routing checks
- End-to-end smoke testing for generated server confidence
- CLI commands: `init`, `generate`, `inspect`, `doctor`, `eval-routing`
- Config via `mcpgen.yaml`
- MIT licensed

## Architecture Flow

```text
OpenAPI spec
  -> parser
  -> tool generator
  -> tool selection
  -> risk classifier
  -> local schema/ref resolver
  -> safety filter
  -> tools.json / tools.all.json / tools.embeddings.json / safety_report.json / tool_catalog.md
  -> generated FastAPI or MCP server
  -> policy engine
  -> semantic/keyword router
  -> dry-run or safe GET execution
  -> audit log
  -> metrics summary
```

## Quick Start

Install locally:

```bash
pip install -e .[dev]
```

Install from PyPI after publishing:

```bash
pip install openapi-mcpgen
```

Optional semantic routing dependency:

```bash
pip install "openapi-mcpgen[semantic]"
```

Create a starter project:

```bash
mcpgen init --directory demo_mcpgen
cd demo_mcpgen
```

For offline development with mock execution enabled:

```bash
mcpgen init --directory demo_mcpgen --profile mock
```

Inspect a spec:

```bash
mcpgen inspect --from openapi.yaml --config mcpgen.yaml
```

Run diagnostics:

```bash
mcpgen doctor --from openapi.yaml --config mcpgen.yaml
```

Run a smoke test:

```bash
mcpgen smoke --from openapi.yaml --config mcpgen.yaml --cases routing_eval.yaml
```

Generate a FastAPI server:

```bash
mcpgen generate --from openapi.yaml --config mcpgen.yaml --mode fastapi --output generated_jsonplaceholder
```

Evaluate routing:

```bash
mcpgen eval-routing --from openapi.yaml --config mcpgen.yaml --cases routing_eval.yaml
```

Run it:

```bash
cd generated_jsonplaceholder
export API_BASE_URL=https://jsonplaceholder.typicode.com
uvicorn server:app --reload --port 8001
```

PowerShell:

```powershell
cd generated_jsonplaceholder
$env:API_BASE_URL = "https://jsonplaceholder.typicode.com"
uvicorn server:app --reload --port 8001
```

Open:

```text
http://127.0.0.1:8001/
http://127.0.0.1:8001/docs
http://127.0.0.1:8001/tools
http://127.0.0.1:8001/safety
http://127.0.0.1:8001/metrics
```

## Example OpenAPI Input

Demo spec:

```text
examples/jsonplaceholder.openapi.yaml
```

It includes:

- `GET /users`
- `GET /users/{id}`
- `GET /posts`
- `GET /posts/{id}`
- `POST /posts`
- `DELETE /posts/{id}`

Excerpt:

```yaml
paths:
  /users/{id}:
    get:
      operationId: getUserById
      summary: Get user by ID
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
```

## Generated Tool Example

Generated safe tool:

```json
{
  "name": "get_user_by_id",
  "description": "Get user by ID",
  "method": "GET",
  "path": "/users/{id}",
  "risk_level": "low",
  "enabled": true,
  "operation_id": "getUserById",
  "input_schema": {
    "type": "object",
    "properties": {
      "id": {
        "type": "integer",
        "description": "User ID",
        "x-mcpgen-location": "path"
      }
    },
    "required": ["id"]
  }
}
```

Withheld tools such as `create_post` and `delete_post` remain in `tools.all.json` and are explained in `safety_report.json`.

## Tool Catalog

Every generated server includes `tool_catalog.md`, a human-readable review file for developers and security reviewers.

It summarizes:

- total selected tools
- exposed safe tools
- withheld tools
- method, path, risk, and exposure status for each tool
- generated input fields
- response fields when response schemas are available

Example:

```markdown
## get_user_by_id

- Method: `GET`
- Path: `/users/{id}`
- Risk: `low`
- Exposed: `yes`

### Inputs

- `id`: integer, required

### Response

- `id`: integer
- `name`: string
- `email`: string
```

## Routing Evaluation

`mcpgen eval-routing` checks whether natural-language queries route to expected safe tools.

Example `routing_eval.yaml`:

```yaml
- query: list all users
  expected:
    - list_users
- query: get user by id
  expected:
    - get_user_by_id
```

Run:

```bash
mcpgen eval-routing --from openapi.yaml --config mcpgen.yaml --cases routing_eval.yaml
```

Example output:

```text
Routing eval: 2/2 passed
Accuracy: 100%
Routing mode: semantic
Top K: 5

[PASS] list all users
Expected: list_users
Returned: list_users, get_user_by_id
```

If any case fails, the command exits with code `1`, making it useful in CI before exposing a generated server to an agent.

## Smoke Tests

`mcpgen smoke` runs a lightweight end-to-end confidence check in a temporary directory.

It checks:

- `doctor` diagnostics
- safe tool exposure
- risky tool withholding
- generated file presence
- generated FastAPI or MCP server importability
- optional routing eval cases

Run:

```bash
mcpgen smoke --from openapi.yaml --config mcpgen.yaml --cases routing_eval.yaml
```

Smoke failures exit with code `1`, so teams can use them in CI before publishing or deploying generated servers.

## Production Readiness

MCPGen is no longer a proof-of-concept MVP. It is an early-stage production-oriented framework with a stable `1.x` developer contract.

Current production-readiness work includes:

- Python 3.10, 3.11, and 3.12 CI matrix
- generated-server smoke tests
- response validation metadata on safe execution and mocks
- example gallery smoke checks
- routing evaluation
- security policy
- config compatibility notes
- changelog and release tags

Remaining maturity work:

- official MCP SDK integration
- broader OpenAPI compatibility testing against real-world specs
- stricter response validation modes
- policy extension hooks
- external audit/metrics sinks
- deployment guides

See [SECURITY.md](SECURITY.md) and [docs/CONFIG_COMPATIBILITY.md](docs/CONFIG_COMPATIBILITY.md).

## Example Gallery

MCPGen includes example scenarios under `examples/`:

- `examples/jsonplaceholder` uses the public JSONPlaceholder API.
- `examples/github-like` demonstrates repository issues, pull requests, bearer passthrough config, and withheld writes.
- `examples/billing-api` demonstrates billing-style tools, API key config, mocks, and withheld invoice writes/deletes.

Each example includes:

- OpenAPI spec
- `mcpgen.yaml`
- `routing_eval.yaml`
- README with expected safety behavior

## FastAPI Demo Commands

From the project root:

```bash
mcpgen generate --from examples/jsonplaceholder.openapi.yaml --mode fastapi --output generated_jsonplaceholder
cd generated_jsonplaceholder
export API_BASE_URL=https://jsonplaceholder.typicode.com
uvicorn server:app --reload --port 8001
```

PowerShell:

```powershell
mcpgen generate --from examples/jsonplaceholder.openapi.yaml --mode fastapi --output generated_jsonplaceholder
cd generated_jsonplaceholder
$env:API_BASE_URL = "https://jsonplaceholder.typicode.com"
uvicorn server:app --reload --port 8001
```

List exposed safe tools:

```bash
curl http://127.0.0.1:8001/tools
```

Route tools by query:

```bash
curl -X POST http://127.0.0.1:8001/tools \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"get user by id\"}"
```

PowerShell equivalent:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/tools `
  -ContentType "application/json" `
  -Body '{"query":"get user by id"}'
```

Dry-run a safe tool:

```bash
curl -X POST http://127.0.0.1:8001/tools/get_user_by_id/dry-run \
  -H "Content-Type: application/json" \
  -d "{\"inputs\":{\"id\":1}}"
```

Execute a safe `GET` tool:

```bash
curl -X POST http://127.0.0.1:8001/execute \
  -H "Content-Type: application/json" \
  -d "{\"tool_name\":\"get_user_by_id\",\"params\":{\"id\":1}}"
```

PowerShell equivalent:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/execute `
  -ContentType "application/json" `
  -Body '{"tool_name":"get_user_by_id","params":{"id":1}}'
```

Show blocked `POST` behavior:

```bash
curl -X POST http://127.0.0.1:8001/tools/create_post/dry-run \
  -H "Content-Type: application/json" \
  -d "{\"inputs\":{\"title\":\"Hello\",\"body\":\"Demo\",\"userId\":1}}"
```

Show blocked `DELETE` behavior:

```bash
curl -X POST http://127.0.0.1:8001/tools/delete_post/dry-run \
  -H "Content-Type: application/json" \
  -d "{\"inputs\":{\"id\":1}}"
```

Show audit log:

```bash
cat logs/audit.log
```

PowerShell equivalent:

```powershell
Get-Content logs\audit.log
```

Show metrics:

```bash
curl http://127.0.0.1:8001/metrics
```

PowerShell equivalent:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/metrics
```

## MCP Mode

Generate an MCP-style stdio server:

```bash
mcpgen generate --from examples/jsonplaceholder.openapi.yaml --mode mcp --output generated_jsonplaceholder_mcp
```

Run:

```bash
cd generated_jsonplaceholder_mcp
export API_BASE_URL=https://jsonplaceholder.typicode.com
python server.py
```

PowerShell:

```powershell
cd generated_jsonplaceholder_mcp
$env:API_BASE_URL = "https://jsonplaceholder.typicode.com"
python server.py
```

Example `tools/list` JSON-RPC input:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list"}
```

Example `tools/call` dry-run input:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_user_by_id","arguments":{"id":1}}}
```

MCP mode uses the same `tools.json`, policy engine, and audit logging as FastAPI mode. In the current MVP, `tools/call` is dry-run by default. With `execution_mode: safe-execute`, it can execute only low-risk `GET` tools.

## Semantic Tool Routing

MCPGen writes `tools.embeddings.json` during generation and uses it when:

```yaml
routing_mode: semantic
```

If embeddings are unavailable or semantic ranking fails, MCPGen automatically falls back to keyword routing. You can force keyword routing with:

```yaml
routing_mode: keyword
```

Tool text combines the tool name, description, and optional tags. Example:

```text
create_invoice create invoice for customer billing payments
```

By default, MCPGen uses a deterministic local embedding fallback so demos and tests work without model downloads. To use the optional `sentence-transformers` backend, install the extra and set the backend:

```bash
pip install "openapi-mcpgen[semantic]"
```

```bash
export MCPGEN_EMBEDDING_BACKEND=sentence-transformers
```

PowerShell:

```powershell
pip install "openapi-mcpgen[semantic]"
$env:MCPGEN_EMBEDDING_BACKEND = "sentence-transformers"
```

Compare routing modes by changing `routing_mode` in `mcpgen.yaml` and regenerating the server. Semantic mode ranks by vector similarity; keyword mode ranks by normalized token overlap and includes matched terms.

## Tool Selection Controls

v0.8.0 adds generation-time controls for narrowing large OpenAPI specs before safety filtering and server generation.

Config:

```yaml
include_tools: []
exclude_tools:
  - delete_user
include_paths:
  - /users*
exclude_paths:
  - /admin/*
  - /internal/*
include_methods:
  - GET
exclude_methods:
  - DELETE
```

Selection is applied before `tools.json`, `tools.all.json`, `tools.embeddings.json`, and `safety_report.json` are written. It never weakens MCPGen safety: excluded tools are removed from the generated surface, but selected `POST`, `PUT`, `PATCH`, and `DELETE` tools are still withheld unless the policy layer allows a safe dry-run or confirmation flow.

Useful commands:

```bash
mcpgen inspect --from examples/jsonplaceholder.openapi.yaml --config mcpgen.yaml
mcpgen doctor --from examples/jsonplaceholder.openapi.yaml --config mcpgen.yaml
```

`inspect` reports discovered, selected, excluded, exposed, and withheld tool counts. `doctor` warns if selection excludes every generated tool.

## OpenAPI Schema Support

v0.9.0 adds better schema handling for real-world specs:

- resolves local refs such as `#/components/schemas/User`
- supports nested objects and arrays after refs are resolved
- merges simple `allOf` object schemas
- extracts JSON response schemas into each generated tool
- uses response schemas to produce more useful mock responses
- warns through `mcpgen doctor` when unresolved refs remain

Example generated tool excerpt:

```json
{
  "name": "get_user_by_id",
  "method": "GET",
  "path": "/users/{id}",
  "response_schema": {
    "type": "object",
    "properties": {
      "id": {"type": "integer"},
      "name": {"type": "string"}
    }
  }
}
```

This is still intentionally MVP-level. Remote refs, complex composition rules, discriminators, and full JSON Schema validation are not implemented yet.

## Safety Model

MCPGen is safe by default:

- Only low-risk `GET` tools are exposed in `tools.json`.
- Medium-risk write tools are withheld unless future config explicitly enables them.
- High-risk `DELETE` tools are always blocked.
- Real execution is restricted to low-risk `GET` tools.
- Write execution is not implemented.
- Auth is not implemented.

Policy decisions return:

```json
{
  "allowed": false,
  "status": "blocked",
  "reason": "Medium-risk tool is not listed in enabled_tools.",
  "risk_level": "medium",
  "tool_name": "create_post"
}
```

## Request Validation

v0.6.0 validates tool inputs before dry-run previews or safe GET execution. Validation uses the generated `input_schema` from OpenAPI parameters and JSON request bodies.

MCPGen currently checks:

- required fields
- basic JSON Schema types: `string`, `integer`, `number`, `boolean`, `array`, `object`
- enum values

Example validation error:

```json
{
  "valid": false,
  "status": "validation_error",
  "tool_name": "get_user_by_id",
  "errors": [
    {
      "field": "id",
      "reason": "required field is missing"
    }
  ]
}
```

Validation runs in:

- FastAPI dry-run: `POST /tools/{tool_name}/dry-run`
- FastAPI safe execution: `POST /execute`
- MCP `tools/call`

This validation is intentionally MVP-level. It catches common input mistakes before network calls, but it is not a full JSON Schema validator yet.

## Response Validation

MCPGen validates successful safe execution and mock responses against generated `response_schema` when one is available.

Example response metadata:

```json
{
  "tool": "get_user_by_id",
  "status": "success",
  "status_code": 200,
  "data": {
    "id": 1,
    "name": "Ada"
  },
  "response_validation": {
    "valid": true,
    "status": "valid",
    "tool_name": "get_user_by_id",
    "errors": []
  }
}
```

Current response validation checks:

- required fields
- basic JSON Schema types
- enum values
- arrays
- nested objects

In `1.4.0`, response validation is reported as metadata and does not block successful upstream responses. This keeps integrations tolerant while still surfacing schema drift. Stricter failure modes are planned for a future release.

## Mock Runtime

v0.7.0 adds mock execution so developers can test generated servers without a live API, database, credentials, or internet access.

v0.9.0 improves mock responses by using OpenAPI response schemas when they are available.

Config:

```yaml
mock:
  enabled: true
  mode: schema
  seed: 123
  list_size: 3
```

When mock mode is enabled, safe `GET` execution returns deterministic mock data instead of calling the upstream API. Policy, validation, rate limiting, audit logging, and metrics still apply. If a tool has a `response_schema`, MCPGen uses it to shape mock objects and arrays.

Example mock response:

```json
{
  "tool": "get_user_by_id",
  "status": "success",
  "status_code": 200,
  "data": {
    "id": 1,
    "name": "Users 1",
    "mock": true
  },
  "mocked": true
}
```

List-style tools return arrays using `mock.list_size`.

## Failure Injection

Failure injection lets developers simulate common upstream failures and observe how their server, agent, or LLM workflow responds.

Config:

```yaml
failure_injection:
  enabled: true
  scenarios:
    get_user_by_id: not_found
    list_posts: timeout
```

Supported MVP scenarios:

- `timeout`
- `not_found`
- `server_error`
- `malformed_json`

Example simulated response:

```json
{
  "tool": "get_user_by_id",
  "status": "error",
  "status_code": 404,
  "data": {
    "error": "Simulated not found."
  },
  "simulated": true
}
```

Failure injection takes precedence over mock mode when both are enabled for the same tool.

## Audit Logging

Audit logs are JSONL records written to:

```text
logs/audit.log
```

Config:

```yaml
audit_enabled: true
audit_log_path: logs/audit.log
routing_mode: semantic
```

Each event includes:

- timestamp
- tool name
- method
- path
- risk level
- mode
- status
- allowed
- reason
- source
- action

Actions include:

- `policy_evaluation`
- `dry_run`
- `execution_started`
- `execution_success`
- `execution_error`
- `execution_blocked`

Audit is the event trail. It answers what happened, when, and why for each attempt.

## Observability Metrics

v0.3.0 adds lightweight aggregate metrics for generated servers. Metrics are stored as JSON at:

```text
logs/metrics.json
```

Config:

```yaml
metrics_enabled: true
metrics_path: logs/metrics.json
```

Metrics track:

- total tool routes
- total policy evaluations
- dry-runs
- execution starts, successes, errors, and blocked attempts
- confirmation-required decisions
- per-tool route, policy, dry-run, execution, success, error, and blocked counts
- average execution latency in milliseconds per tool
- last updated timestamp

FastAPI mode exposes:

```text
GET /metrics
POST /metrics/reset
```

Example response:

```json
{
  "total_tool_routes": 1,
  "total_policy_evaluations": 2,
  "total_executions": 1,
  "total_execution_success": 1,
  "total_execution_errors": 0,
  "total_execution_blocked": 1,
  "total_dry_runs": 1,
  "total_confirmation_required": 0,
  "per_tool": {
    "get_user_by_id": {
      "routed": 1,
      "policy_allowed": 2,
      "policy_blocked": 0,
      "dry_runs": 1,
      "executions": 1,
      "successes": 1,
      "errors": 0,
      "blocked": 0,
      "average_execution_latency_ms": 42.5
    }
  },
  "last_updated": "2026-05-05T12:00:00+00:00"
}
```

Metrics are MVP-level and file-based. They are useful for local demos and development visibility, but they are not a replacement for production telemetry systems.

## Rate Limiting

v0.5.0 adds lightweight in-memory rate limiting for generated servers.

Config:

```yaml
rate_limit:
  enabled: true
  per_tool: 10
  global: 100
  window_seconds: 60
```

Defaults:

```yaml
rate_limit:
  enabled: false
  per_tool: 10
  global: 100
  window_seconds: 60
mock:
  enabled: false
  mode: schema
  seed: 123
  list_size: 3
failure_injection:
  enabled: false
  scenarios: {}
```

FastAPI mode applies the global limit to operational requests:

- `POST /tools`
- `POST /tools/{tool_name}/dry-run`
- `POST /execute`

Per-tool limits apply to:

- `POST /tools/{tool_name}/dry-run`
- `POST /execute`
- MCP `tools/call`

Health and root endpoints are not rate limited.

When a request exceeds the limit, FastAPI returns `429` with a `Retry-After` header:

```json
{
  "status": "rate_limited",
  "scope": "per_tool",
  "retry_after": 30,
  "reason": "rate limit exceeded"
}
```

Rate-limited events are recorded in both audit logs and aggregate metrics:

- `total_rate_limited`
- `per_tool.<tool>.rate_limited`

Limitations: rate limiting is in-memory only, resets when the generated server restarts, and is not distributed across processes or machines. Redis and distributed rate limiting are intentionally out of scope for this MVP.

## Auth Passthrough

v0.4.0 adds safe upstream authentication support for generated servers. Secrets are never written into generated files, audit logs, metrics, or responses.

Default config:

```yaml
auth:
  mode: none
  api_key_env: API_KEY
  api_key_header: X-API-Key
```

### mode: none

No auth headers are sent upstream.

```yaml
auth:
  mode: none
```

### mode: bearer_passthrough

FastAPI mode can forward an incoming `Authorization` header to the upstream API only when it starts with `Bearer `.

```yaml
auth:
  mode: bearer_passthrough
```

Example request:

```bash
curl -X POST http://127.0.0.1:8001/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"tool_name\":\"get_user_by_id\",\"params\":{\"id\":1}}"
```

PowerShell:

```powershell
$env:TOKEN = "your-token"
Invoke-RestMethod -Method Post http://127.0.0.1:8001/execute `
  -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer $env:TOKEN" } `
  -Body '{"tool_name":"get_user_by_id","params":{"id":1}}'
```

MCP stdio mode does not have HTTP headers. For `bearer_passthrough`, provide explicit auth metadata in `tools/call` arguments:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_user_by_id",
    "arguments": {
      "id": 1,
      "auth": {
        "authorization": "Bearer your-token"
      }
    }
  }
}
```

The `auth` metadata is stripped before tool parameter handling and is not logged.

### mode: api_key

API key mode reads a key from an environment variable and injects it into the configured upstream header.

```yaml
auth:
  mode: api_key
  api_key_env: JSONPLACEHOLDER_API_KEY
  api_key_header: X-API-Key
```

Bash:

```bash
export JSONPLACEHOLDER_API_KEY=your-api-key
```

PowerShell:

```powershell
$env:JSONPLACEHOLDER_API_KEY = "your-api-key"
```

If the environment variable is missing, `/execute` returns a clear error and does not call the upstream API.

OAuth2 is not implemented yet. It is listed in the roadmap.

## Configuration

Default config:

```yaml
max_tools: 5
allowed_methods:
  - GET
include_tools: []
exclude_tools: []
include_paths: []
exclude_paths: []
include_methods: []
exclude_methods: []
output_dir: generated_mcp_server
api_base_url: https://api.example.com
enabled_tools: []
execution_mode: dry-run
audit_enabled: true
audit_log_path: logs/audit.log
routing_mode: semantic
metrics_enabled: true
metrics_path: logs/metrics.json
auth:
  mode: none
  api_key_env: API_KEY
  api_key_header: X-API-Key
rate_limit:
  enabled: false
  per_tool: 10
  global: 100
  window_seconds: 60
```

For the JSONPlaceholder demo, set:

```yaml
api_base_url: https://jsonplaceholder.typicode.com
```

## Doctor Diagnostics

`mcpgen doctor` runs read-only checks against an OpenAPI spec and optional config file:

```bash
mcpgen doctor --from examples/jsonplaceholder.openapi.yaml --config mcpgen.yaml
```

It checks:

- config loading and validation
- OpenAPI parseability
- generated server smoke checks
- execution mode
- routing mode
- API base URL readiness
- auth mode
- rate limit settings
- metrics and audit settings
- tool selection rules
- generated tool counts
- exposed vs withheld tools
- potential tool overload against `max_tools`

Example output:

```text
MCPGen doctor: warn
[PASS] config: Config loaded successfully.
[PASS] openapi: Parsed 6 endpoint(s).
[WARN] api_base_url: api_base_url is using the default placeholder.
[PASS] tool_selection: Tool selection config is valid.
[PASS] safety: 4 low-risk tool(s) will be exposed.
```

`doctor` exits with code `1` if a failing check is found, which makes it useful in CI.

## Current Limitations

- This is a production-oriented MVP, not a production-ready framework.
- Auth support is limited to bearer passthrough and API key header injection.
- Request validation is MVP-level and not full JSON Schema validation.
- Mock responses are deterministic fixtures shaped by response schemas when available, not realistic domain datasets.
- Failure injection is configured per tool and supports only common MVP scenarios.
- Tool selection supports simple names, methods, and shell-style path wildcards, not full OpenAPI tag/group policies yet.
- Schema support resolves local refs and simple `allOf`, but not remote refs, discriminators, or complex composition.
- No OAuth2 flow yet.
- No write execution.
- No confirmation workflow UI.
- No vector database or embedding cache optimization.
- Rate limiting is in-memory only and not distributed.
- No database-backed audit sink.
- No production telemetry backend.
- MCP mode uses a minimal stdio scaffold if the official Python MCP SDK is unavailable.

## Roadmap

- Official MCP SDK integration
- OAuth2 support
- Confirmation workflow for enabled medium-risk tools
- Response validation
- Full JSON Schema validation
- OpenAPI tag-based tool selection
- Failure scenario probabilities and per-request overrides
- Pluggable audit sinks
- Better semantic routing models and embedding cache optimization
- Deployment templates

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Publishing

MCPGen publishes through GitHub Actions using PyPI Trusted Publishing. No PyPI API token should be committed to the repository.

Workflow:

```text
.github/workflows/publish.yml
```

Recommended flow:

1. Configure Trusted Publishing on TestPyPI for this repository and the `Publish Python Package` workflow.
2. Run the workflow manually with `repository = testpypi`.
3. Install and verify from TestPyPI.
4. Configure Trusted Publishing on PyPI.
5. Publish a GitHub Release or run the workflow manually with `repository = pypi`.

Install from TestPyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple openapi-mcpgen
```

Install from PyPI:

```bash
pip install openapi-mcpgen
```
