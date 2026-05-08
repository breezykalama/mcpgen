# Config Compatibility

MCPGen `1.x` treats the current `mcpgen.yaml` keys as the first stable developer config contract.

## Compatibility Promise

Within `1.x`:

- existing config keys should not be removed without a deprecation period
- existing defaults should remain safe by default
- new config keys should be optional
- generated servers should continue to read `mcpgen.runtime.json`
- write execution should not become enabled by default
- high-risk `DELETE` tools should remain blocked by default
- response validation should remain non-blocking unless a future explicit strict mode is configured

## Stable Config Areas

- `max_tools`
- `allowed_methods`
- `include_tools`
- `exclude_tools`
- `include_paths`
- `exclude_paths`
- `include_methods`
- `exclude_methods`
- `output_dir`
- `api_base_url`
- `enabled_tools`
- `execution_mode`
- `audit_enabled`
- `audit_log_path`
- `routing_mode`
- `metrics_enabled`
- `metrics_path`
- `auth`
- `rate_limit`
- `mock`
- `failure_injection`
- `circuit_breaker`

## Experimental Config Areas

These may evolve with clearer migration notes:

- semantic routing backend behavior
- failure injection scenario names
- mock data shape realism
- future MCP SDK-specific options

## Migration Guidance

When changing MCPGen versions:

1. Run `mcpgen doctor --from openapi.yaml --config mcpgen.yaml`.
2. Run `mcpgen smoke --from openapi.yaml --config mcpgen.yaml --cases routing_eval.yaml`.
3. Review generated `tool_catalog.md`.
4. Review `safety_report.json`.
5. Run `mcpgen watchdog --from openapi.yaml --config mcpgen.yaml --cases routing_eval.yaml`.
