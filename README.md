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
- semantic tool routing with keyword fallback

The default behavior is intentionally conservative: only low-risk `GET` tools are exposed.

## Features

- OpenAPI YAML/JSON parsing
- Tool generation from endpoints
- Risk classification:
  - `GET` = low
  - `POST`, `PUT`, `PATCH` = medium
  - `DELETE` = high
- Safe-by-default filtering
- Input schema generation from path/query parameters and JSON request bodies
- Semantic tool routing with keyword fallback
- FastAPI mode
- MCP stdio mode with `tools/list` and `tools/call`
- Dry-run request previews
- Safe real execution for low-risk `GET` tools only
- Central policy engine
- JSONL audit logging
- CLI commands: `generate`, `inspect`
- Config via `mcpgen.yaml`

## Architecture Flow

```text
OpenAPI spec
  -> parser
  -> tool generator
  -> risk classifier
  -> safety filter
  -> tools.json / tools.all.json / tools.embeddings.json / safety_report.json
  -> generated FastAPI or MCP server
  -> policy engine
  -> semantic/keyword router
  -> dry-run or safe GET execution
  -> audit log
```

## Quick Start

Install locally:

```bash
pip install -e .[dev]
```

Inspect a spec:

```bash
mcpgen inspect --from examples/jsonplaceholder.openapi.yaml
```

Generate a FastAPI server:

```bash
mcpgen generate --from examples/jsonplaceholder.openapi.yaml --mode fastapi --output generated_jsonplaceholder
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

By default, MCPGen uses a deterministic local embedding fallback so demos and tests work without model downloads. To use `sentence-transformers`, set:

```bash
export MCPGEN_EMBEDDING_BACKEND=sentence-transformers
```

PowerShell:

```powershell
$env:MCPGEN_EMBEDDING_BACKEND = "sentence-transformers"
```

Compare routing modes by changing `routing_mode` in `mcpgen.yaml` and regenerating the server. Semantic mode ranks by vector similarity; keyword mode ranks by normalized token overlap and includes matched terms.

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

## Configuration

Default config:

```yaml
max_tools: 5
allowed_methods:
  - GET
output_dir: generated_mcp_server
api_base_url: https://api.example.com
enabled_tools: []
execution_mode: dry-run
audit_enabled: true
audit_log_path: logs/audit.log
```

For the JSONPlaceholder demo, set:

```yaml
api_base_url: https://jsonplaceholder.typicode.com
```

## Current Limitations

- This is a production-oriented MVP, not a production-ready framework.
- No authentication or secret handling beyond environment-variable preparation.
- No write execution.
- No confirmation workflow UI.
- No vector database or embedding cache optimization.
- No rate limiting.
- No database-backed audit sink.
- MCP mode uses a minimal stdio scaffold if the official Python MCP SDK is unavailable.

## Roadmap

- Official MCP SDK integration
- Auth and secret management
- Confirmation workflow for enabled medium-risk tools
- Rate limiting
- Request/response validation
- Better OpenAPI schema support
- Pluggable audit sinks
- Better semantic routing models and embedding cache optimization
- Deployment templates
