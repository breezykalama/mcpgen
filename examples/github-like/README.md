# GitHub-like Example

Repository workflow example with read tools, a medium-risk create action, and a high-risk delete action.

Run:

```bash
mcpgen smoke --from examples/github-like/openapi.yaml --config examples/github-like/mcpgen.yaml --cases examples/github-like/routing_eval.yaml
mcpgen generate --from examples/github-like/openapi.yaml --config examples/github-like/mcpgen.yaml --output generated_github_like
```

Expected behavior:

- `list_issues` and `list_pull_requests` are exposed.
- `create_issue` is withheld as medium risk.
- `delete_issue` is withheld as high risk.
- Mock mode is enabled so safe execution does not require a live upstream API.
