"""
Memory repositories for Agent Core.

Implements the DynamoDB schemas described in feature_1.md:

Short-term (session) memory:
PK: TENANT#<tenant_id>#SESSION#<session_id>
SK: MSG#<timestamp>

Mid-term / long-term can evolve later; for now we model the same shape
for simplicity and future extension.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from agent_core.config.settings import AgentCoreSettings, load_settings
from agent_core.models.memory import MemoryMessage
from agent_core.repositories.dynamo_base import query_items


class MemoryRepository:
    def __init__(self, settings: AgentCoreSettings | None = None) -> None:
        self._settings = settings or load_settings()
        self._short_table = self._settings.dynamo.table_name("memory_short_term")
        self._mid_table = self._settings.dynamo.table_name("memory_mid_term")
        self._long_table = self._settings.dynamo.table_name("memory_long_term")

    # === Short-term (session) memory ===

    def load_short_term(
        self, tenant_id: str, session_id: str, limit: int = 20
    ) -> List[MemoryMessage]:
        pk = f"TENANT#{tenant_id}#SESSION#{session_id}"
        items = query_items(
            self._short_table,
            "PK = :pk",
            {":pk": {"S": pk}},
            limit=limit,
            scan_index_forward=False,  # newest first
        )
        messages = [MemoryMessage.from_dynamo(it) for it in items]
        # Return newest first already; caller can slice
        return messages

    # === Mid-term memory (last ~48h or N interactions) ===

    def load_mid_term(
        self, tenant_id: str, user_id: str, hours: int = 48, limit: int = 50
    ) -> List[MemoryMessage]:
        """
        Simple heuristic: query by PK prefix and then filter by timestamp
        client-side. Real implementation would likely use GSI + TTL.
        """
        # For now we reuse the same table as short-term or a dedicated one.
        # We'll use a synthetic PK so future table design can honour this.
        pk = f"TENANT#{tenant_id}#USER#{user_id}"
        items = query_items(
            self._mid_table,
            "PK = :pk",
            {":pk": {"S": pk}},
            limit=limit,
            scan_index_forward=False,
        )

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result: List[MemoryMessage] = []
        for it in items:
            msg = MemoryMessage.from_dynamo(it)
            try:
                ts = datetime.fromisoformat(msg.timestamp.replace("Z", "+00:00"))
            except ValueError:
                continue
            if ts >= cutoff:
                result.append(msg)
        return result

    # === Long-term memory (preferences, patterns) ===

    def load_long_term(
        self, tenant_id: str, user_id: str, limit: int = 50
    ) -> List[MemoryMessage]:
        pk = f"TENANT#{tenant_id}#USER#{user_id}#LONG_TERM"
        items = query_items(
            self._long_table,
            "PK = :pk",
            {":pk": {"S": pk}},
            limit=limit,
            scan_index_forward=True,
        )
        return [MemoryMessage.from_dynamo(it) for it in items]



