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


def test_parse_openapi_resolves_local_refs_and_all_of(tmp_path: Path) -> None:
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(
        """
        openapi: 3.0.0
        info:
          title: Example
          version: 1.0.0
        paths:
          /posts:
            post:
              operationId: createPost
              requestBody:
                content:
                  application/json:
                    schema:
                      $ref: "#/components/schemas/PostInput"
              responses:
                "201":
                  description: Created
                  content:
                    application/json:
                      schema:
                        $ref: "#/components/schemas/Post"
        components:
          schemas:
            PostInput:
              type: object
              required:
                - title
              properties:
                title:
                  type: string
            Post:
              allOf:
                - $ref: "#/components/schemas/PostInput"
                - type: object
                  required:
                    - id
                  properties:
                    id:
                      type: integer
        """,
        encoding="utf-8",
    )

    endpoints = parse_openapi(spec_path)

    request_schema = endpoints[0].request_body["content"]["application/json"]["schema"]
    response_schema = endpoints[0].responses["201"]["content"]["application/json"]["schema"]
    assert request_schema["properties"]["title"]["type"] == "string"
    assert "$ref" not in request_schema
    assert response_schema["type"] == "object"
    assert response_schema["required"] == ["title", "id"]
    assert response_schema["properties"]["id"]["type"] == "integer"
