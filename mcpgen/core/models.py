from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Endpoint(BaseModel):
    operation_id: str | None = None
    summary: str | None = None
    description: str | None = None
    method: str
    path: str
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    request_body: dict[str, Any] | None = None


class Tool(BaseModel):
    name: str
    description: str
    method: str
    path: str
    risk_level: RiskLevel
    enabled: bool = True
    operation_id: str | None = None
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    request_body: dict[str, Any] | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)


class GenerationResult(BaseModel):
    output_dir: str
    tools: list[Tool]
    mode: str = "fastapi"
    all_tools: list[Tool] = Field(default_factory=list)
    safety_report: dict[str, Any] = Field(default_factory=dict)
