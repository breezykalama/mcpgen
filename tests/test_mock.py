from mcpgen.runtime.mock import build_mock_response


def list_users_tool() -> dict:
    return {
        "name": "list_users",
        "method": "GET",
        "path": "/users",
        "input_schema": {
            "type": "object",
            "properties": {
                "active": {"type": "boolean"},
            },
        },
    }


def get_user_tool() -> dict:
    return {
        "name": "get_user_by_id",
        "method": "GET",
        "path": "/users/{id}",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "x-mcpgen-location": "path"},
                "include": {"type": "string", "enum": ["profile", "posts"]},
            },
            "required": ["id"],
        },
    }


def test_mock_list_tool_returns_array() -> None:
    result = build_mock_response(
        list_users_tool(),
        {},
        {"mock": {"enabled": True, "seed": 123, "list_size": 2}},
    )

    assert result["status"] == "success"
    assert result["mocked"] is True
    assert result["response_validation"]["status"] == "skipped"
    assert len(result["data"]) == 2
    assert result["data"][0]["mock"] is True


def test_mock_get_by_id_returns_object_using_params() -> None:
    result = build_mock_response(
        get_user_tool(),
        {"id": 42},
        {"mock": {"enabled": True, "seed": 123, "list_size": 2}},
    )

    assert result["data"]["id"] == 42
    assert result["data"]["include"] == "profile"
    assert result["data"]["mock"] is True


def test_mock_uses_response_schema_when_available() -> None:
    tool = {
        "name": "list_users",
        "method": "GET",
        "path": "/users",
        "input_schema": {},
        "response_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "address": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"},
                        },
                    },
                },
            },
        },
    }

    result = build_mock_response(
        tool,
        {},
        {"mock": {"enabled": True, "seed": 123, "list_size": 2}},
    )

    assert len(result["data"]) == 2
    assert result["response_validation"]["valid"] is True
    assert result["data"][0]["id"] == 1
    assert result["data"][0]["name"] == "name_1"
    assert result["data"][0]["address"]["city"] == "city_1"
