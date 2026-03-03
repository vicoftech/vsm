"""
STEP 2 — Memory Load

Initial implementation: placeholders for short/mid/long term memories.
They can later be wired to dedicated DynamoDB tables with TTLs.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from agent_core.config.settings import AgentCoreSettings
from agent_core.models.agent_context import AgentContext, MemoryLayer
from agent_core.repositories.memory_repo import MemoryRepository


def run(
    ctx: AgentContext,
    *,
    settings: AgentCoreSettings,
    extra: Dict[str, Any],
) -> Tuple[AgentContext, Dict[str, Any]]:
    """
    Load short/mid/long term memories from DynamoDB.

    All operations are best-effort: if the tables don't exist yet, the
    repository simply returns empty lists and the agent sigue funcionando.
    """
    repo = MemoryRepository(settings=settings)

    short_msgs = repo.load_short_term(ctx.tenant_id, ctx.session_id, limit=20)
    mid_msgs = repo.load_mid_term(
        ctx.tenant_id, ctx.user_id or "anonymous", hours=48, limit=50
    )
    long_msgs = repo.load_long_term(ctx.tenant_id, ctx.user_id or "anonymous", limit=50)

    new_ctx = ctx.with_updates(
        short_term_memory=MemoryLayer(
            items=[{"role": m.role, "content": m.content, "timestamp": m.timestamp} for m in short_msgs]
        ),
        mid_term_memory=MemoryLayer(
            items=[{"role": m.role, "content": m.content, "timestamp": m.timestamp} for m in mid_msgs]
        ),
        long_term_memory=MemoryLayer(
            items=[{"role": m.role, "content": m.content, "timestamp": m.timestamp} for m in long_msgs]
        ),
    )

    return new_ctx, {}



