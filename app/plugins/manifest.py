"""Plugin manifest Pydantic models."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, field_validator


class PluginType(StrEnum):
    qa_check = "qa_check"
    agent_skill = "agent_skill"
    export_connector = "export_connector"
    component_package = "component_package"
    theme = "theme"
    workflow_step = "workflow_step"


class PluginPermission(StrEnum):
    read_templates = "read_templates"
    read_components = "read_components"
    read_qa_results = "read_qa_results"
    write_qa_results = "write_qa_results"
    call_llm = "call_llm"
    network_access = "network_access"
    file_read = "file_read"


class PluginMetadata(BaseModel):
    author: str = ""
    description: str = ""
    homepage: str = ""
    license: str = ""
    tags: list[str] = []


class PluginManifest(BaseModel):
    name: str  # reverse domain: com.example.my-plugin
    version: str  # semver
    hub_api_version: str  # e.g. ">=1.0"
    plugin_type: PluginType
    entry_point: str  # Python module path
    permissions: list[PluginPermission] = []
    config_schema: dict[str, Any] | None = None
    metadata: PluginMetadata = PluginMetadata()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9._-]{2,63}$", v):
            msg = "Plugin name must be 3-64 chars, lowercase, start with letter, contain only [a-z0-9._-]"
            raise ValueError(msg)
        return v

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+", v):
            msg = "Version must follow semver (e.g. 1.0.0)"
            raise ValueError(msg)
        return v
