"""
Permissions repository.

Backed by DynamoDB table `skill_permissions` as described in feature_1.md:

PK: TENANT#<tenant_id>#USER#<user_id>
SK: SKILL#<skill_name>
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from agent_core.config.settings import AgentCoreSettings, load_settings
from agent_core.repositories.dynamo_base import get_item


@dataclass
class SkillPermission:
    skill_name: str
    allowed: bool
    rules: List[str]
    mcp_target: str
    rate_limit_per_day: int


class PermissionsRepository:
    def __init__(self, settings: AgentCoreSettings | None = None) -> None:
        self._settings = settings or load_settings()
        self._table = self._settings.dynamo.table_name("skill_permissions")

    def _pk(self, tenant_id: str, user_id: str) -> str:
        return f"TENANT#{tenant_id}|USER#{user_id}"

    def _sk(self, skill_name: str) -> str:
        return f"SKILL#{skill_name}"

    def get_permission(
        self, tenant_id: str, user_id: str, skill_name: str
    ) -> SkillPermission | None:
        """
        Load a single skill permission for a user.

        For now we use a simple GetItem by PK/SK. In a real single-table
        design we'd likely also support Query for all skills.
        """
        item = get_item(
            self._table,
            {
                "PK": {"S": self._pk(tenant_id, user_id)},
                "SK": {"S": self._sk(skill_name)},
            },
        )
        if not item:
            return None

        def _get(name: str, default: Any = None) -> Any:
            return item.get(name, {}).get("S") or item.get(name, {}).get("N") or default

        allowed = item.get("allowed", {}).get("BOOL", False)
        rules_raw = item.get("rules", {}).get("SS", [])

        return SkillPermission(
            skill_name=skill_name,
            allowed=allowed,
            rules=list(rules_raw),
            mcp_target=_get("mcp_target", "jira"),
            rate_limit_per_day=int(_get("rate_limit_per_day", "100")),
        )




