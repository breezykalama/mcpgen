# JSONPlaceholder Example

Public demo API for exercising safe GET execution, response schemas, routing, audit logs, and metrics.

Run:

```bash
mcpgen smoke --from examples/jsonplaceholder.openapi.yaml --config examples/jsonplaceholder/mcpgen.yaml --cases examples/jsonplaceholder/routing_eval.yaml
mcpgen generate --from examples/jsonplaceholder.openapi.yaml --config examples/jsonplaceholder/mcpgen.yaml --output generated_jsonplaceholder
```

Expected behavior:

- `list_users`, `get_user_by_id`, `list_posts`, and `get_post_by_id` are exposed.
- `create_post` and `delete_post` are withheld or blocked by policy.
- Routing eval cases should pass.
