from pathlib import Path


VALID_PROFILES = {"safe", "mock"}


def init_project(directory: Path, profile: str = "safe", force: bool = False) -> list[Path]:
    """Create a small MCPGen starter workspace."""
    profile = profile.lower()
    if profile not in VALID_PROFILES:
        raise ValueError(f"profile must be one of: {', '.join(sorted(VALID_PROFILES))}")

    files = {
        directory / "mcpgen.yaml": starter_config(profile),
        directory / ".env.example": "API_BASE_URL=https://jsonplaceholder.typicode.com\n",
        directory / "openapi.yaml": starter_openapi_spec(),
        directory / "routing_eval.yaml": starter_routing_eval(),
    }

    directory.mkdir(parents=True, exist_ok=True)
    written = []

    for path, content in files.items():
        if path.exists() and not force:
            raise FileExistsError(f"{path} already exists. Use --force to overwrite starter files.")
        path.write_text(content, encoding="utf-8")
        written.append(path)

    return written


def starter_config(profile: str) -> str:
    mock_enabled = "true" if profile == "mock" else "false"
    return f"""max_tools: 5
allowed_methods:
  - GET
include_tools: []
exclude_tools: []
include_paths: []
exclude_paths: []
include_methods: []
exclude_methods: []
output_dir: generated_mcp_server
api_base_url: https://jsonplaceholder.typicode.com
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
mock:
  enabled: {mock_enabled}
  mode: schema
  seed: 123
  list_size: 3
failure_injection:
  enabled: false
  scenarios: {{}}
circuit_breaker:
  enabled: false
  failure_threshold: 5
  recovery_seconds: 60
retry:
  enabled: false
  max_attempts: 3
  backoff_seconds: 0.5
  retry_statuses:
    - 429
    - 500
    - 502
    - 503
    - 504
"""


def starter_openapi_spec() -> str:
    return """openapi: 3.0.0
info:
  title: MCPGen Starter API
  version: 1.0.0
servers:
  - url: https://jsonplaceholder.typicode.com
paths:
  /users:
    get:
      operationId: listUsers
      summary: List users
      responses:
        "200":
          description: Users
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: "#/components/schemas/User"
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
      responses:
        "200":
          description: User
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/User"
components:
  schemas:
    User:
      type: object
      required:
        - id
        - name
        - email
      properties:
        id:
          type: integer
        name:
          type: string
        email:
          type: string
"""


def starter_routing_eval() -> str:
    return """- query: list all users
  expected:
    - list_users
- query: get user by id
  expected:
    - get_user_by_id
"""
