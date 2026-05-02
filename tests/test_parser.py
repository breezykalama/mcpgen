from pathlib import Path

from mcpgen.core.parser import parse_openapi


def test_parse_openapi_yaml_extracts_supported_methods() -> None:
    endpoints = parse_openapi(Path("examples/openapi.yaml"))

    assert len(endpoints) == 5
    assert endpoints[0].method == "GET"
    assert endpoints[0].path == "/customers"
    assert endpoints[0].operation_id == "listCustomers"


def test_parse_openapi_json(tmp_path: Path) -> None:
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(
        """
        {
          "openapi": "3.0.0",
          "info": {"title": "Example", "version": "1.0.0"},
          "paths": {
            "/users/{userId}": {
              "get": {
                "operationId": "getUser",
                "summary": "Get user",
                "parameters": [
                  {"name": "userId", "in": "path", "required": true}
                ]
              }
            }
          }
        }
        """,
        encoding="utf-8",
    )

    endpoints = parse_openapi(spec_path)

    assert len(endpoints) == 1
    assert endpoints[0].parameters[0]["name"] == "userId"

