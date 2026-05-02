import json
from pathlib import Path

from mcpgen.core.models import Tool


class ToolRegistry:
    """Loads and stores generated tool descriptors."""

    def __init__(self, tools: list[Tool]) -> None:
        self._tools = tools

    @classmethod
    def from_json(cls, path: Path) -> "ToolRegistry":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls([Tool.model_validate(item) for item in data])

    def list_tools(self) -> list[Tool]:
        return list(self._tools)

    def get_tool(self, name: str) -> Tool | None:
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None
