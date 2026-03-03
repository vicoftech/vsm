"""
STEP 2 — Memory Load

Initial implementation: placeholders for short/mid/long term memories.
They can later be wired to dedicated DynamoDB tables with TTLs.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from agent_core.config.settings import AgentCoreSettings
from agent_core.models.agent_context import AgentContext, MemoryLayer


def run(
    ctx: AgentContext,
    *,
    settings: AgentCoreSettings,
    extra: Dict[str, Any],
) -> Tuple[AgentContext, Dict[str, Any]]:
    # TODO: Load memories from DynamoDB tables:
    # - memory_short_term
    # - memory_mid_term
    # - memory_long_term
    #
    # For now we just keep them empty but explicitly populated.

    new_ctx = ctx.with_updates(
        short_term_memory=MemoryLayer(items=[]),
        mid_term_memory=MemoryLayer(items=[]),
        long_term_memory=MemoryLayer(items=[]),
    )

    return new_ctx, {}



