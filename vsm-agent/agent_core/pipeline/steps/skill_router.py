"""
STEP 4 — Skill & Rule Routing

Validates that:
- The skill resolved in STEP 3 exists and is enabled (future `skills_catalog`).
- The user has permission to execute the skill (via `skill_permissions`).

In this first version we only check permissions if a skill was found.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from agent_core.config.settings import AgentCoreSettings
from agent_core.models.agent_context import AgentContext
from agent_core.repositories.permissions_repo import PermissionsRepository


def run(
    ctx: AgentContext,
    *,
    settings: AgentCoreSettings,
    extra: Dict[str, Any],
) -> Tuple[AgentContext, Dict[str, Any]]:
    # If no skill was resolved, we leave the context as fallback candidate
    if not ctx.resolved_skill_id:
        return ctx, {}

    repo = PermissionsRepository(settings=settings)
    perm = repo.get_permission(ctx.tenant_id, ctx.user_id or "anonymous", ctx.resolved_skill_id)

    if not perm or not perm.allowed:
        # Permission denied — mark context as fallback/error but let
        # resilience handler build the final user-facing message.
        new_ctx = ctx.with_updates(
            final_status="fallback",
            fallback_message="No tenés permisos para ejecutar esta acción.",
        )
        return new_ctx, {}

    # For now we don't apply rule-level logic; that will be added later.
    new_ctx = ctx.with_updates(
        resolved_mcp_target=perm.mcp_target,
        allowed_skills=[ctx.resolved_skill_id],
    )
    return new_ctx, {}



