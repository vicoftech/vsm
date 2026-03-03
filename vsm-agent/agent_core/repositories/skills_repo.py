"""
Skills catalog repository.

Backed by DynamoDB table `skills_catalog` with schema:

PK: SKILL#<skill_id>
SK: <version> (e.g., "v1")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agent_core.config.settings import AgentCoreSettings, load_settings
from agent_core.repositories.dynamo_base import get_item


@dataclass
class Skill:
    skill_id: str
    version: str
    mcp_target: str
    mcp_tool: str
    description: str
    input_schema: Dict[str, Any]
    rules: List[str]
    enabled: bool


class SkillsRepository:
    def __init__(self, settings: AgentCoreSettings | None = None) -> None:
        self._settings = settings or load_settings()
        self._table = self._settings.dynamo.table_name("skills_catalog")

    def _pk(self, skill_id: str) -> str:
        return f"SKILL#{skill_id}"

    def get_skill(
        self, skill_id: str, version: str = "v1"
    ) -> Optional[Skill]:
        item = get_item(
            self._table,
            {
                "PK": {"S": self._pk(skill_id)},
                "SK": {"S": version},
            },
        )
        if not item:
            return None

        def _s(name: str, default: str = "") -> str:
            return item.get(name, {}).get("S", default)

        enabled = item.get("enabled", {}).get("BOOL", True)
        rules_raw = item.get("rules", {}).get("SS", [])
        input_schema = item.get("input_schema", {}).get("M", {})

        return Skill(
            skill_id=skill_id,
            version=version,
            mcp_target=_s("mcp_target", "jira"),
            mcp_tool=_s("mcp_tool", ""),
            description=_s("description", ""),
            input_schema=input_schema,
            rules=list(rules_raw),
            enabled=enabled,
        )



