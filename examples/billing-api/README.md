# Billing API Example

Billing-style API that demonstrates API key config, mock mode, routing evals, and safe withholding of write/delete operations.

Run:

```bash
mcpgen smoke --from examples/billing-api/openapi.yaml --config examples/billing-api/mcpgen.yaml --cases examples/billing-api/routing_eval.yaml
mcpgen generate --from examples/billing-api/openapi.yaml --config examples/billing-api/mcpgen.yaml --output generated_billing
```

Expected behavior:

- `list_customers` and `list_invoices` are exposed.
- `create_customer` and `create_invoice` are withheld as medium risk.
- `delete_invoice` is withheld as high risk.
- Mock mode is enabled for offline development.
