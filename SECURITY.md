# Security Policy

MCPGen is a production-oriented framework, but it should still be reviewed before use with sensitive internal APIs.

## Supported Versions

Security fixes are expected to target the latest released version.

## Reporting a Vulnerability

Please report security issues privately by opening a GitHub security advisory or contacting the maintainer through the repository owner profile.

Do not publish working exploits, API tokens, credentials, or private OpenAPI specifications in public issues.

## Current Security Model

MCPGen is safe by default:

- only low-risk `GET` tools are exposed in `tools.json`
- medium-risk write tools are withheld unless explicitly enabled for policy review
- high-risk `DELETE` tools are always blocked
- real execution is limited to low-risk `GET` tools
- audit logs and metrics sanitize credential-like values
- generated servers do not hardcode secrets
- API keys are read from environment variables

## Security Limitations

- OAuth2 is not implemented yet.
- Write execution is not implemented yet.
- Confirmation workflows for write tools are not implemented yet.
- File-based audit and metrics are not a production telemetry backend.
- Generated servers should be placed behind the deployment platform's normal authentication, network, and monitoring controls.

## Recommended Production Review

Before using MCPGen with sensitive APIs:

- run `mcpgen inspect`
- run `mcpgen doctor`
- run `mcpgen smoke`
- review `tool_catalog.md`
- review `safety_report.json`
- verify auth configuration
- verify logs do not contain credentials
- run routing evals for expected user queries
